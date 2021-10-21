# -*- coding: utf-8 -*-
"""
Created on Mon Jan 11 17:11:38 2021

@author: Dean

Uncertainty estimation for the WISPER ORACLES measurements.

2016 calibration parameters will be used to get uncertainty estimates. However, 
the uncertainties derived using the 2016 parameters are assumed to be 
representative for all ORACLES years.
"""

    
# Third party:
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

# My modules:
import pic1_cal # Has Pic1 calibration functions.
import precisions
import mc_sampler as mc



def wisper_uncertainties_MC(d, q, calparams, sig_calparams, sig_d=None):
    """
    Compute uncertainties for dD using monte carlo sampling.
    Plot the results. Then, fit a polynomial to the uncertainties as a fxn of 
    q and dD.
    
    Inputs
    ------
    d, q: ND np.arrays, same shape.
        Values for isotope ratio (either dD or d18O) and humidity.    
    
    calparams: 4-element list/array-like. 
        First 2 elements are the 'a' and 'b' parameters in the humidity-
        dependence formula. Second 2 elements are the slope and intercept of 
        the absolute calibration. 
    
    sig_calparams: 4-element list/array-like; 
        Uncertainties for 'params', as stdevs.
    
    sig_d: None or np.array same shape as q.
        Default=None. Use to include measurement uncertainties (i.e. 
        instrument precision) in the total computation of WISPER uncertainties.
        
    Returns uncertainties in same shape as q.
    """    
    
    def pic1_isoratio_fullcal(d, q, calparams):
        """
        Full calibration of either dD or d18O for Pic1.
        
        d, q, calparams: 
            As in the header of the encompassing fxn. 
        """
        d_qdep_correct = pic1_cal.q_dep_cal(d, q, 
                                            calparams[0], calparams[1])
        d_abscal = pic1_cal.abs_cal(d_qdep_correct, 
                                   calparams[2], calparams[3])
        return d_abscal
    
    
    ## Monte Carlo iterations with the full cal model:
    #q, d = np.meshgrid(np.linspace(1500,22000,100), np.linspace(-300,-60,150))
        
    if sig_d is not None: # Include instrument precisions.
        sig_q = np.zeros(np.shape(q)) # q is precise enough to ignore.
        #sig_dD = precisions.dD_precision_pic1(q)
        results = mc.mc_normalsampler(pic1_isoratio_fullcal, [d,q], 
                                      calparams, sig_calparams, 
                                      6000,
                                      sig_inputvars=[sig_d, sig_q], 
                                      return_agg=True
                                      )
    else:
        results = mc.mc_normalsampler(pic1_isoratio_fullcal, [d,q], 
                                      calparams, sig_calparams, 
                                      6000, return_agg=True
                                      )

    return results



def fit_poly(q, d, sig_d):
    """
    Fit standard deviations to a polynomial function of humidity and isoratio.
    
    df_forfit = pd.DataFrame({'logq':np.log(q.flatten()),
                                  'dD':d.flatten(),
                                  'sig_dD':results[1].flatten()})

    """
    # Put vars in a pandas df to use with the statsmodel package:
    df_forfit = pd.DataFrame({'logq':np.log(q),
                              'd':d,
                              'sig_d':sig_d})
    
    # Add columns for powers of q. Add column for constant offset:
    for p in (2,3,4):
        df_forfit['logq^'+str(p)] = df_forfit['logq']**p
        df_forfit['const'] = np.ones(len(df_forfit))

    # Linear regression using statsmodels
    predictorvars = ['const','logq','logq^2','logq^3','logq^4','d']
    fit = sm.OLS(df_forfit['sig_d'], df_forfit[predictorvars], missing='drop').fit()            
    #print(fit.summary())  
    #print(fit.params)
    print(np.round(fit.rsquared, decimals=2))
            
    return fit.params 



def get_calparams(iso, sig_absoffset):
    """
    Returns means and standard deviations for all parameters in the 
    isotope ratio calibration formulas.
    
    iso: str.
        Either 'D' or '18O' for isotopologue.
    """
    
    ## Means:
        # Load humidity-dependence cal param data for 2016:
    pars_qdep = pd.read_csv(r"../calibration_modelling/humidity_dependence/"
                            + "qdependence_fit_results.csv")
    pars_qdep_16 = pars_qdep.loc[(pars_qdep['picarro']=='Mako')
                                 & (pars_qdep['year']==2016)]
    pars_qdep = pars_qdep_16[['a'+iso,'b'+iso]].values[0] 
        # Hard code abs cal parameters:
    if iso=='D':
        m = 1.0564; k = -5.957469671 
    if iso=='18O':
        m = 1.051851852; k = -1.041851852
        # Combine into a single list:
    pars = np.append(pars_qdep, [m, k])


    ## Standard deviations:
        # For humidity dependence params:
    sigpars_qdep = pars_qdep_16[['sig_aD','sig_bD']].values[0] 
        # For abs cal params:
    if iso=='D':
        sigm = 0.0564/2; sigk = sig_absoffset
    if iso=='18O':
        sigm = 0.05185/2; sigk = sig_absoffset
        # Combine into a single list:
    sigpars = np.append(sigpars_qdep, [sigm, sigk])         
        
    
    return pars, sigpars
           
    

def get_isoprecisions(iso, q):
    """
    iso: str.
        Either 'D' or '18O' for isotopologue.
        
    q: ND np.array.
        Humidities, used to compute precicions.
    """
    if iso=='D':
        return precisions.dD_precision_pic1(q)
    if iso=='18O':    
        return precisions.d18O_precision_pic1(q)


            
def wisper_sig_formula(q, d, pars):
    """
    Formula for either dD or d18O uncertainties as a function of q and the 
    respective isotope ratio (see also 'fit_poly').
    
    q, d: ND np.array's, same size.
        Values for humidity and one of dD or d18O.
        
    pars: array-like, length=6.
        Parameters in the fit formula.
    """
    return pars[0] + pars[1]*np.log(q) + pars[2]*np.log(q)**2 + \
        pars[3]*np.log(q)**3 + pars[4]*np.log(q)**4 + pars[5]*d    



def wisper_uncertainties_with_fit():
    """
    Currently for dD only.
    """
    
    q, d = np.meshgrid(np.linspace(1500,22000,100), np.linspace(-300,-60,150))

    # (2) Uncertainties when averaging data to 0.1Hz or lower, or 
    # comparing PDFs:
        # Calibration pars expected values and standard deviations:
    std_absoffset = 1
    calparams = get_calparams('D', std_absoffset)
    sigWISP2_D = wisper_uncertainties_MC(d, q, calparams[0], calparams[1], sig_d=None)[1]


    ## Plot of Monte Carlo standard devs:  
    p = plt.scatter(q, d, c=sigWISP2_D, cmap='gist_ncar', vmin=2, vmax=10)
    plt.colorbar()
    
    ## Get polynomial fit:
    parsD_fit2 = fit_poly(q.flatten(), d.flatten(), sigWISP2_D.flatten())
               
    plt.figure()
    p1 = plt.scatter(q, d, c=wisper_sig_formula(q, d, parsD_fit2.values), 
                     cmap='gist_ncar', vmin=2, vmax= 10)
    plt.colorbar()

#-------------------
    """    
## dD 
       # (1) Uncertainties when using the 1Hz WISPER measurements for 
        # relative comparisons:    
    sigpars_qdep_D = pars_qdep_16[['sig_aD','sig_bD']].values[0] 
    sig_mD = 0.0564/2; sig_kD = 1 # No offset needed for relative comparisons.
    sigpars_all_D = np.append(sigpars_qdep_D, [sig_mD,sig_kD])
    sigWISP1_D = sigma_with_fit_dD(pars_all_D, sigpars_all_D, sig_inputvars=True)
    
        # (2) Uncertainties when averaging data to 0.1Hz or lower, or 
        # comparing PDFs:
    sigWISP2_D = sigma_with_fit_dD(pars_all_D, sigpars_all_D)
    
        # (3) Uncertainties when comparing WISPER 0.1Hz data or PDFs to other 
        # datasets, or to absolute theoretical values:
    sig_kD = 4. # Now we care about absolute offset.
    sigpars_all_D = np.append(sigpars_qdep_D, [sig_mD,sig_kD])
    sigWISP3_D = sigma_with_fit_dD(pars_all_D, sigpars_all_D, 
                                   ax_cax=(ax_sigD, cax_sigD))

    ## d18O:
        # (1) Uncertainties when using the 1Hz WISPER measurements for 
        # relative comparisons:
    sigpars_qdep_18O = pars_qdep_16[['sig_a18O','sig_b18O']].values[0] 
    sig_m18O = 0.05185/2; sig_k18O = 1./2 # Offset needed for d18O due to drift.
    sigpars_all_18O = np.append(sigpars_qdep_18O, [sig_m18O,sig_k18O])
    sigWISP1_18O = sigma_with_fit_d18O(pars_all_18O, sigpars_all_18O, 
                                       sig_inputvars=True)
    
        # (2) Uncertainties when averaging data to 0.1Hz or lower, or 
        # comparing PDFs:
    sigWISP2_18O = sigma_with_fit_d18O(pars_all_18O, sigpars_all_18O)

        # (3) Uncertainties when comparing WISPER 0.1Hz data or PDFs to other 
        # datasets, or to absolute theoretical values:
    sig_k18O = 1. # Now we care about absolute offset.
    sigpars_all_18O = np.append(sigpars_qdep_18O, [sig_m18O,sig_k18O])
    sigWISP3_18O = sigma_with_fit_d18O(pars_all_18O, sigpars_all_18O, 
                                       ax_cax=(ax_sig18O, cax_sig18O))
    
    """
    
    
    

def pic1_uncertainties():
        
    """
    Runs full calibration of either dD or d18O for Pic1:
        d: dD or d18O values (np.array like).
        q: humidity values (np.array like, same shape as dD).
        calparams: 4-element list/array-like. First 2 elements are the 'a' and 
            'b' parameters in the humidity dependence formula. Second 2 elements 
            are the slope and intercept of the absolute calibration.
    """
    #def pic1_isoratio_fullcal(d, q, calparams):
    #    
    #    d_qdep_correct = pic1_cal.q_dep_cal(d, q, 
    #                                        calparams[0], calparams[1])
    #    d_abscal = pic1_cal.abs_cal(d_qdep_correct, 
    #                               calparams[2], calparams[3])
    #    return d_abscal
            
     
    """
    Following two functions compute uncertainties for dD and d18O 
    respectively. The results are plotted. Then, a polynomial is fit to the 
    uncertainties as a fxn of q and the respective isotope ratio.
    
    params: 4-element list/array-like. First 2 elements are the 'a' and 
        'b' parameters in the humidity dependence formula. Second 2 elements 
        are the slope and intercept of the absolute calibration. 
    sig_params: 4-element list/array-like; uncertainties for params, as stdevs.
    sig_inputvars: default=False. If True, include measurement 
        uncertainties (i.e. instrument precision) in the total 
        computation of WISPER uncertainties.
    ax_cax: 2-tuple of matplotlib.pyplot axes. 1st is for plotting the monte 
        carlo derived standard deviations, 2nd is for the color scale.
        
    Returns the polynomial fit parameters for the monte carlo derived 
    uncertainties.
    """    
    def sigma_with_fit_dD(params, sig_params, sig_inputvars=False, 
                          ax_cax=None):
    ##-------------------------------------------------------------------------
        ## Monte Carlo computation of uncertainties over a regularly-spaced 
        ## humidity (ppmv) vs. dD (permil) map:
        q, d = np.meshgrid(np.linspace(1500,22000,100), np.linspace(-300,-60,150))
            
        if sig_inputvars: # Include instrument precisions?
            sig_q = np.zeros(np.shape(q)) # q is precise enough to ignore.
            sig_dD = precisions.dD_precision_pic1(q)
            results = mc.mc_normalsampler(pic1_isoratio_fullcal, [d,q], 
                                          params, sig_params, 
                                          6000,
                                          sig_inputvars=[sig_dD, sig_q]
                                          )
        else:
            results = mc.mc_normalsampler(pic1_isoratio_fullcal, [d,q], 
                                          params, sig_params, 
                                          6000,
                                          )
         
            
        ## Optional plot of Monte Carlo standard devs:  
        if ax_cax is not None:
            p = ax_cax[0].scatter(q, d, c=results[1], cmap='gist_ncar', 
                                  vmin=2, vmax= 10)
            plt.colorbar(p, cax=ax_cax[1], orientation='horizontal')
            
            
        ## Fit standard deviation map to polynomial fxn of q and isoratio:
            # Put vars in a pandas df to use with the statsmodel package:
        df_forfit = pd.DataFrame({'logq':np.log(q.flatten()),
                                  'dD':d.flatten(),
                                  'sig_dD':results[1].flatten()})
            
            # Add columns for powers of q. Add column for constant offset:
        for p in (2,3,4):
            df_forfit['logq^'+str(p)] = df_forfit['logq']**p
        df_forfit['const'] = np.ones(len(df_forfit))

            # Run linear regression with statsmodels
        #predictorvars = ['const','logq','logq^2','dD']
        predictorvars = ['const','logq','logq^2','logq^3','logq^4','dD']
        fit = sm.OLS(df_forfit['sig_dD'], df_forfit[predictorvars], missing='drop').fit()            
        #print(fit.summary())     
        #print(fit.params)
        print(np.round(fit.rsquared, decimals=2))


        return fit.params 
    ##-------------------------------------------------------------------------
                
            
    def sigma_with_fit_d18O(params, sig_params, sig_inputvars=False, 
                            ax_cax=None):
    ##-------------------------------------------------------------------------
        ## Monte Carlo computation of uncertainties over a regularly-spaced 
        ## humidity (ppmv) vs. d18O (permil) map:
        q, d = np.meshgrid(np.linspace(1500,22000,100), np.linspace(-30,-8,150))
            
        if sig_inputvars: # Include instrument precisions?
            sig_q = np.zeros(np.shape(q)) # q is precise enough to ignore.
            sig_d18O = precisions.d18O_precision_pic1(q)
            results = mc.mc_normalsampler(pic1_isoratio_fullcal, [d,q], 
                                          params, sig_params, 
                                          6000,
                                          sig_inputvars=[sig_d18O, sig_q]
                                          )
        else:
            results = mc.mc_normalsampler(pic1_isoratio_fullcal, [d,q], 
                                          params, sig_params, 
                                          6000,
                                          )
            

        ## Optional plot of Monte Carlo standard devs:  
        if ax_cax is not None:
            p = ax_cax[0].scatter(q, d, c=results[1], cmap='gist_ncar', 
                                  vmin=0.2, vmax=5)
            plt.colorbar(p, cax=ax_cax[1], orientation='horizontal')
            
            
        ## Fit standard deviation map to polynomial fxn of q and isoratio:
            # Put vars in a pandas df to use with the statsmodel package:
        df_forfit = pd.DataFrame({'logq':np.log(q.flatten()),
                                  'd18O':d.flatten(),
                                  'sig_d18O':results[1].flatten()})
            # Add columns for powers of q. Add column for constant offset:
        for p in (2,3,4):
            df_forfit['logq^'+str(p)] = df_forfit['logq']**p
        df_forfit['const'] = np.ones(len(df_forfit))

            # Run linear regression with statsmodels
        #predictorvars = ['const','logq','logq^2','d18O']
        predictorvars = ['const','logq','logq^2','logq^3','logq^4','d18O']
        fit = sm.OLS(df_forfit['sig_d18O'], df_forfit[predictorvars], missing='drop').fit()            
        #print(fit.summary())  
        #print(fit.params)
        print(np.round(fit.rsquared, decimals=2))
        
        
        return fit.params 
    ##-------------------------------------------------------------------------
    

    fig = plt.figure(figsize=(6.5,2.75))
    ax_sigD = fig.add_axes([0.1,0.175,0.38,0.6])
    cax_sigD = fig.add_axes([0.1,0.9,0.38,0.05])
    ax_sig18O = fig.add_axes([0.6,0.175,0.38,0.6])
    cax_sig18O = fig.add_axes([0.6,0.9,0.38,0.05])
   
    
    ## dD uncertainties:
    ##-------------------------------------------------------------------------
    ## Collect expected values for calibration parameters into a list.
        # Load humidity-dependence calibration parameter fits for 2016:
    relpath_qdepcal_pars = (r"../calibration_modelling/humidity_dependence/"
                            + "qdependence_fit_results.csv")
    pars_qdep = pd.read_csv(relpath_qdepcal_pars)
    pars_qdep_16 = pars_qdep.loc[(pars_qdep['picarro']=='Mako')
                                 & (pars_qdep['year']==2016)]
    pars_qdep_D = pars_qdep_16[['aD','bD']].values[0] 
        # Hard code absolute calibration parameters:
    m_D = 1.0564; k_D = -5.957469671
        # Collect in list to pass to one of my above fxns:
    pars_all_D = np.append(pars_qdep_D, [m_D,k_D]) 

    
    ## Run monte carlo simulation for 3 sets of parameter + measurement 
    ## uncertainty combos:
    
        # (1) Uncertainties when using the 1Hz WISPER measurements for 
        # relative comparisons:    
    sigpars_qdep_D = pars_qdep_16[['sig_aD','sig_bD']].values[0] 
    sig_mD = 0.0564/2; sig_kD = 1 # No offset needed for relative comparisons.
    sigpars_all_D = np.append(sigpars_qdep_D, [sig_mD,sig_kD])
    sigWISP1_D = sigma_with_fit_dD(pars_all_D, sigpars_all_D, sig_inputvars=True)
    
        # (2) Uncertainties when averaging data to 0.1Hz or lower, or 
        # comparing PDFs:
    sigWISP2_D = sigma_with_fit_dD(pars_all_D, sigpars_all_D)
    
        # (3) Uncertainties when comparing WISPER 0.1Hz data or PDFs to other 
        # datasets, or to absolute theoretical values:
    sig_kD = 4. # Now we care about absolute offset.
    sigpars_all_D = np.append(sigpars_qdep_D, [sig_mD,sig_kD])
    sigWISP3_D = sigma_with_fit_dD(pars_all_D, sigpars_all_D, 
                                   ax_cax=(ax_sigD, cax_sigD))
    ##-------------------------------------------------------------------------
    
    
    ## d18O uncertainties:
    ##-------------------------------------------------------------------------
    ## Collect expected values for calibration parameters into a list.
        # Humidity-dependence calibration parameter fits for 2016:
    pars_qdep_18O = pars_qdep_16[['a18O','b18O']].values[0] 
        # Hard code absolute calibration params:
    m_18O = 1.051851852; k_18O = -1.041851852
        # Collect in list to pass to one of my above fxns:
    pars_all_18O = np.append(pars_qdep_18O, [m_18O,k_18O])             


    ## Run monte carlo simulation for 3 sets of parameter + measurement 
    ## uncertainty combos:
    
        # (1) Uncertainties when using the 1Hz WISPER measurements for 
        # relative comparisons:
    sigpars_qdep_18O = pars_qdep_16[['sig_a18O','sig_b18O']].values[0] 
    sig_m18O = 0.05185/2; sig_k18O = 1./2 # Offset needed for d18O due to drift.
    sigpars_all_18O = np.append(sigpars_qdep_18O, [sig_m18O,sig_k18O])
    sigWISP1_18O = sigma_with_fit_d18O(pars_all_18O, sigpars_all_18O, 
                                       sig_inputvars=True)
    
        # (2) Uncertainties when averaging data to 0.1Hz or lower, or 
        # comparing PDFs:
    sigWISP2_18O = sigma_with_fit_d18O(pars_all_18O, sigpars_all_18O)

        # (3) Uncertainties when comparing WISPER 0.1Hz data or PDFs to other 
        # datasets, or to absolute theoretical values:
    sig_k18O = 1. # Now we care about absolute offset.
    sigpars_all_18O = np.append(sigpars_qdep_18O, [sig_m18O,sig_k18O])
    sigWISP3_18O = sigma_with_fit_d18O(pars_all_18O, sigpars_all_18O, 
                                       ax_cax=(ax_sig18O, cax_sig18O))
    ##-------------------------------------------------------------------------
    
    
    ## Collect WISPER uncertainty map parameter fits into a pandas df:
    idx_levnames = ('use case','isotope')
    idx_labs = (['1','2','3'],['dD','d18O'])
    multi_idx = pd.MultiIndex.from_product(idx_labs, names=idx_levnames)
    sigWISP_df = pd.DataFrame(np.zeros([6,6]),
                              index=multi_idx, 
                              columns=('alph0','alph1','alph2','alph3','alph4','alph5')
                              )
    
    for case, pD, p18O in zip(['1','2','3'],
                        [sigWISP1_D, sigWISP2_D, sigWISP3_D], 
                        [sigWISP1_18O, sigWISP2_18O, sigWISP3_18O]):
        sigWISP_df.loc[(case,'dD')] = pD.values
        sigWISP_df.loc[(case,'d18O')] = p18O.values
        
    sigWISP_df = sigWISP_df.round(dict(zip(sigWISP_df.columns, [1,1,2,3,4,4])))
    print(sigWISP_df)       
 
    
    ## Compute WISPER uncertainties for some typical q, dD, d18O values in 
    ## the MBL, cloud layer, BB-loaded free tropo, and clean free tropo:
        # Fit fxn for either dD or d18O. 
    def wisper_sigfit(q, d, pars):
        return pars[0] + pars[1]*np.log(q) + pars[2]*np.log(q)**2 + \
               pars[3]*np.log(q)**3 + pars[4]*np.log(q)**4 + pars[5]*d
 
    print('MBL dD values\n=========')
    q_mbl = 15000; dD_mbl = -70; d18O_mbl = -10
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('1','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('2','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('3','dD')].values))
   
    print('BB-plume dD values\n=========')
    q_mbl = 6000; dD_mbl = -100; d18O_mbl = -14
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('1','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('2','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('3','dD')].values))
    
    print('Clean FT dD values\n=========')
    q_mbl = 3000; dD_mbl = -150; d18O_mbl = -20
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('1','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('2','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('3','dD')].values))
    
    print('Very clean FT dD values\n=========')
    q_mbl = 1700; dD_mbl = -250; d18O_mbl = -34
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('1','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('2','dD')].values))
    print(wisper_sigfit(q_mbl, dD_mbl, sigWISP_df.loc[('3','dD')].values))
    
    print('MBL d18O values\n=========')
    q_mbl = 15000; dD_mbl = -70; d18O_mbl = -10
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('1','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('2','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('3','d18O')].values))
   
    print('BB-plume d18O values\n=========')
    q_mbl = 6000; dD_mbl = -100; d18O_mbl = -14
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('1','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('2','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('3','d18O')].values))
    
    print('Clean FT d18O values\n=========')
    q_mbl = 3000; dD_mbl = -150; d18O_mbl = -20
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('1','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('2','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('3','d18O')].values))
    
    print('Very clean FT d18O values\n=========')
    q_mbl = 1700; dD_mbl = -250; d18O_mbl = -34
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('1','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('2','d18O')].values))
    print(wisper_sigfit(q_mbl, d18O_mbl, sigWISP_df.loc[('3','d18O')].values))
    
    
    q, d18O = np.meshgrid(np.linspace(1500,22000,100), np.linspace(-30,-8,150))
    q, dD = np.meshgrid(np.linspace(1500,22000,100), np.linspace(-300,-60,150))
    mod_sigdD = wisper_sigfit(q, dD, sigWISP_df.loc[('3','dD')].values)
    mod_sigd18O = wisper_sigfit(q, d18O, sigWISP_df.loc[('3','d18O')].values)

    fig = plt.figure(figsize=(6.5,2.75))
    ax1 = fig.add_axes([0.1,0.175,0.38,0.6])
    cax1 = fig.add_axes([0.1,0.9,0.38,0.05])
    ax2 = fig.add_axes([0.6,0.175,0.38,0.6])
    cax2 = fig.add_axes([0.6,0.9,0.38,0.05])
    

    p1 = ax1.scatter(q, dD, c=mod_sigdD, cmap='gist_ncar', 
                          vmin=2, vmax= 10)
    plt.colorbar(p1, cax=cax1, orientation='horizontal')

    p2 = ax2.scatter(q, d18O, c=mod_sigd18O, cmap='gist_ncar', 
                     vmin=0.2, vmax=5)
    plt.colorbar(p2, cax=cax2, orientation='horizontal')
    
    
    ## Save calibration parameter fit table to .csv file:
    sigWISP_df.to_csv(r"./uncertainty_params.csv")
            
            
#pic1_uncertainties()