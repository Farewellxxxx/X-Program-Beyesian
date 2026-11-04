"""Observation-only, monotone Bayesian model averaging for motion execution.

Factor the standardized residual law as W~N(0,Lambda),
y|W~N(X beta+W c,sigma2). Proper NIG/IW priors give closed-form updates
and evidence; only the monotonicity normalization needs 1D quadrature.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math

import numpy as np
from scipy.integrate import quad
from scipy.special import logsumexp
from scipy.stats import invwishart, t as student_t

from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def frozen_array(value):
    # Bytes-backed arrays cannot be made writeable again by a caller.
    array=np.asarray(value,dtype='<f8')
    return np.frombuffer(array.tobytes(),dtype='<f8').reshape(array.shape)


@dataclass(frozen=True)
class PosteriorSettings:
    bias_prior_sd: float=.50
    gain_prior_sd: float=.50
    quadratic_prior_sd: float=.75
    conditional_prior_sd: float=1.
    sigma_shape: float=2.
    sigma_rate: float=1.
    lambda_df: float=4.
    lambda_scale: float=1.
    posterior_draws: int=2048
    max_design_condition: float=1e8
    max_proposals: int=200000

    def __post_init__(self):
        if any(not math.isfinite(v) or v<=0 for v in asdict(self).values()):
            raise ValueError('Posterior settings must be finite and positive')
        for value in (self.posterior_draws,self.max_proposals):
            if isinstance(value,bool) or not isinstance(value,int): raise ValueError('Draw counts must be integers')
        if self.sigma_shape<=1 or self.lambda_df<=3 or self.max_proposals<self.posterior_draws:
            raise ValueError('Require finite prior covariance means and sufficient proposal budget')

    def fingerprint(self): return fingerprint(asdict(self))


@dataclass(frozen=True)
class RegressionPosterior:
    mean: np.ndarray
    v: np.ndarray
    a: float
    b: float
    log_evidence: float


def fit_regression(design,response,prior_sd,settings=PosteriorSettings()):
    h=np.asarray(design,dtype=float); y=np.asarray(response,dtype=float); sd=np.asarray(prior_sd,dtype=float)
    if h.ndim!=2 or y.shape!=(len(h),) or sd.shape!=(h.shape[1],) or not len(h):
        raise ValueError('Incompatible regression dimensions')
    if not all(np.isfinite(v).all() for v in (h,y,sd)) or (sd<=0).any(): raise ValueError('Invalid regression inputs')
    precision=np.diag(1/sd**2)+h.T@h
    v=np.linalg.solve(precision,np.eye(h.shape[1])); mean=np.linalg.solve(precision,h.T@y)
    a=settings.sigma_shape+len(y)/2
    b=settings.sigma_rate+.5*(np.sum((y-h@mean)**2)+np.sum((mean/sd)**2))
    evidence=math.lgamma(a)-math.lgamma(settings.sigma_shape)+settings.sigma_shape*math.log(settings.sigma_rate)-a*math.log(b)
    evidence+=.5*(np.linalg.slogdet(v)[1]-2*np.log(sd).sum())-len(y)/2*math.log(2*math.pi)
    return RegressionPosterior(frozen_array(mean),frozen_array(v),a,float(b),float(evidence))


def monotone_probability(mean,scale,df,degree,span):
    if degree==0: return 1.
    mean=np.asarray(mean); scale=np.asarray(scale)
    if degree==1: return float(student_t.sf((-.94-mean[1])/np.sqrt(scale[1,1]),df))
    if degree!=2: raise ValueError('Degree must be 0, 1 or 2')
    qsd=np.sqrt(scale[2,2]); conditional=scale[1,1]-scale[1,2]**2/scale[2,2]
    # Integrate in standardized q coordinates to resolve narrow posteriors.
    def integrand(z):
        q=mean[2]+qsd*z
        location=mean[1]+scale[1,2]/qsd*z
        sd=np.sqrt((df+z*z)/(df+1)*conditional)
        return float(student_t.pdf(z,df)*student_t.sf((-.94+span*abs(q)-location)/sd,df+1))
    split=-mean[2]/qsd
    value=sum(quad(integrand,lo,hi,epsabs=1e-9,epsrel=1e-9,limit=200)[0] for lo,hi in [(-np.inf,split),(split,np.inf)])
    if not 0<value<=1+1e-9: raise ValueError('Unable to normalize monotone posterior')
    return min(1.,value)


@dataclass(frozen=True)
class PosteriorComponent:
    degree: int
    regression: RegressionPosterior
    prior_constraint_mass: float
    posterior_constraint_mass: float
    log_evidence: float
    coefficients: np.ndarray
    covariances: np.ndarray
    eta: np.ndarray
    sigma2: np.ndarray
    proposals: int


@dataclass(frozen=True)
class ExecutionPosterior:
    components: tuple
    weights: np.ndarray
    settings: PosteriorSettings
    n_observations: int
    n_used: int
    n_clipped: int
    design_condition: float
    seed_fingerprint: str
    draw_fingerprint: str

    def moments(self,adaptive=True):
        weights=self.weights if adaptive else np.array([0.,0.,1.])
        beta=sum(w*c.coefficients.mean(0) for w,c in zip(weights,self.components))
        cov=sum(w*c.covariances.mean(0) for w,c in zip(weights,self.components))
        return beta,cov

    def metadata(self):
        beta,cov=self.moments()
        result=dict(execution_estimator='adaptive_posterior',fit_settings_fingerprint=self.settings.fingerprint(),
            fit_seed_fingerprint=self.seed_fingerprint,fit_draw_fingerprint=self.draw_fingerprint,
            fit_posterior_draws=self.settings.posterior_draws,fit_map_degree=int(np.argmax(self.weights)),
            fit_expected_degree=float(self.weights@np.arange(3)),fit_model_entropy=float(-np.sum(self.weights*np.log(self.weights))),
            fit_bias=float(beta[0]),fit_gain=float(beta[1]),fit_quadratic=float(beta[2]),
            fit_design_condition=self.design_condition,calibration_n_observations=self.n_observations,
            calibration_n_used=self.n_used,calibration_n_clipped=self.n_clipped,
            belief_execution_bias=float(beta[0]),belief_execution_noise_scale=float(np.sqrt(np.trace(cov)/3)))
        for i in range(3):
            for j in range(i,3): result[f'fit_cov_{i}{j}']=float(cov[i,j])
        for w,c in zip(self.weights,self.components):
            k=c.degree; result.update({f'fit_weight_{k}':float(w),f'fit_log_evidence_{k}':c.log_evidence,
                f'fit_prior_mass_{k}':c.prior_constraint_mass,f'fit_posterior_mass_{k}':c.posterior_constraint_mass,
                f'fit_proposals_{k}':c.proposals})
            for j,name in enumerate(('bias','gain','quadratic')):
                result[f'fit_degree{k}_{name}_mean']=float(c.coefficients[:,j].mean())
                result[f'fit_degree{k}_{name}_sd']=float(c.coefficients[:,j].std())
        return result


def fit_execution_posterior(observations,public_settings,posterior_settings=PosteriorSettings()):
    settings=posterior_settings
    if not set(sim.CALIBRATION_FIELDS).issubset(observations.columns): raise ValueError('Missing calibration channels')
    values=observations[sim.CALIBRATION_FIELDS].to_numpy(dtype='<f8')
    if len(values)<8 or not np.isfinite(values).all(): raise ValueError('At least eight finite observations required')
    lower=np.array([public_settings.x_min,.20,.25,2.20]); upper=np.array([public_settings.x_max,2.40,5.70,4.85])
    if ((values<lower)|(values>upper)).any(): raise ValueError('Calibration outside supported bounds')
    interior=((values[:,1:]>lower[1:])&(values[:,1:]<upper[1:])).all(1)
    x,a,j,t=values[interior].T; n=len(x)
    if n<8: raise ValueError('At least eight unclipped observations required')
    span=public_settings.x_max-public_settings.x_min; d=x-(public_settings.x_min+public_settings.x_max)/2
    level=(x-public_settings.x_min)/span; sa=.045+.055*level; sj=.18+.24*level
    design=np.column_stack([np.ones(n),d,d*d])/sa[:,None]; condition=float(np.linalg.cond(design))
    if np.linalg.matrix_rank(design)!=3 or condition>settings.max_design_condition: raise ValueError('Unidentifiable command design')
    y=(a-.05-.94*x)/sa; w=np.column_stack([(j-.58-1.74*a-.10*x)/sj,(t-3.90+.30*a)/.18])
    seed_settings=asdict(settings); seed_settings.pop('posterior_draws'); seed_settings.pop('max_proposals')
    seed_hash=hashlib.sha256(values.tobytes()+fingerprint(dict(public=asdict(public_settings),settings=seed_settings)).encode()).hexdigest()
    entropy=np.frombuffer(bytes.fromhex(seed_hash),dtype='<u4').tolist()
    components=[]; draw_hash=hashlib.sha256()
    for degree in range(3):
        count=degree+1; sd=np.array([settings.bias_prior_sd,settings.gain_prior_sd,settings.quadratic_prior_sd][:count]+[settings.conditional_prior_sd]*2)
        r=fit_regression(np.column_stack([design[:,:count],w]),y,sd,settings)
        zprior=monotone_probability(np.zeros(len(sd)),settings.sigma_rate/settings.sigma_shape*np.diag(sd**2),2*settings.sigma_shape,degree,span)
        zpost=monotone_probability(r.mean,r.b/r.a*r.v,2*r.a,degree,span)
        rng=np.random.default_rng(np.random.SeedSequence([*entropy,degree,1]))
        lambda_rng=np.random.default_rng(np.random.SeedSequence([*entropy,degree,2]))
        chol=np.linalg.cholesky(r.v); accepted_eta=[]; accepted_sigma=[]; total=0; proposals=0
        while total<settings.posterior_draws:
            batch=min(256,settings.max_proposals-proposals)
            if batch<=0: raise ValueError('Monotone posterior rejection proposal budget exhausted')
            sigma=r.b/rng.gamma(r.a,size=batch)
            eta=r.mean+np.sqrt(sigma)[:,None]*(rng.standard_normal((batch,len(sd)))@chol.T)
            beta=np.zeros((batch,3)); beta[:,:count]=eta[:,:count]
            keep=.94+beta[:,1]>=span*np.abs(beta[:,2])
            accepted_eta.append(eta[keep]); accepted_sigma.append(sigma[keep]); total+=int(keep.sum()); proposals+=batch
        eta=np.concatenate(accepted_eta)[:settings.posterior_draws]; sigma=np.concatenate(accepted_sigma)[:settings.posterior_draws]
        # Fixed chunks preserve exact sample prefixes when the requested count grows.
        lambdas=[]
        for start in range(0,settings.posterior_draws,256):
            lambdas.append(invwishart.rvs(df=settings.lambda_df+n,scale=settings.lambda_scale*np.eye(2)+w.T@w,size=256,random_state=lambda_rng))
        lam=np.concatenate(lambdas)[:settings.posterior_draws]
        beta=np.zeros((len(eta),3)); beta[:,:count]=eta[:,:count]; c=eta[:,count:]
        cross=np.einsum('ni,nij->nj',c,lam)
        cov=np.empty((len(eta),3,3)); cov[:,1:,1:]=lam; cov[:,0,1:]=cross; cov[:,1:,0]=cross
        cov[:,0,0]=sigma+np.einsum('ni,ni->n',cross,c)
        draw_hash.update(np.asarray(beta,dtype='<f8').tobytes()); draw_hash.update(np.asarray(cov,dtype='<f8').tobytes())
        components.append(PosteriorComponent(degree,r,zprior,zpost,r.log_evidence+math.log(zpost)-math.log(zprior),
            frozen_array(beta),frozen_array(cov),frozen_array(eta),frozen_array(sigma),proposals))
    evidence=np.array([c.log_evidence for c in components]); weights=np.exp(evidence-logsumexp(evidence))
    return ExecutionPosterior(tuple(components),frozen_array(weights),settings,len(values),n,int((~interior).sum()),condition,seed_hash,draw_hash.hexdigest())
