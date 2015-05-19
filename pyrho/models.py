
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mp # For plotStates
from .utilities import plotLight
from scipy.signal import * #for argrelextrema
from scipy.integrate import odeint
import warnings

from .parameters import *
#print(vars()['verbose'])
from .config import verbose, addTitles, saveFigFormat, fDir # For plotStates()
#from __init__ import verbose



###### Model class definitions ######

def selectModel(nStates):
    """Model selection function"""
    if nStates == 3:
        return RhO_3states() #(E)
    elif nStates == 4:
        return RhO_4states() #(E,gam,phi0)
    elif nStates == 6:
        return RhO_6states() #(E,gam,phi0,A)
    else:
        print("Error in selecting model - please choose from 3, 4 or 6 states")
        raise NotImplementedError(nStates)
        

class OGmodel(object):
    "Common base class for all models"
    
    phi = 0.0  # Instantaneous Light flux
#     phi0 = 1e14 # Normalising light intensity parameter [photons * s^-1 * mm^-2] ~ 1/10 of threshold
    
    # Solver parameters
#     dt = 0.1 #0.01 #0.1 #0.001
    
    def __init__(self, nStates): #, rhoType='Rhodopsin'
        self.nStates = nStates
        #self.rhoType = rhoType # E.g. 'ChR2' or 'ArchT'
        
    def __str__(self):
        str = self.rhoType+" {} state model (phi={:.3g})".format(self.nStates,self.phi) # Display transition rates?
        #if self.useIR:
        #    str += " with inward rectification"
        return str
        #self.__name__+

    def __call__(self):
        """When a rhodopsin is called, return its internal state at that instant"""
        return self.calcI(self.V, self.states[-1,:])
    
    def setParams(self, params):
        """Set all model parameters from a Parameters() object"""
        #for param, value in params.items():
        for p in params.keys():
            self.__dict__[p] = params[p].value #vars(self())[p]
    
    def updateParams(self, params):
        """Update model parameters which already exist"""
        pDict = params.valuesdict()
        count = 0
        for p, v in pDict.items():
            if p in self.__dict__: # Added to allow dummy variables in fitting parameters
                self.__dict__[p] = v #vars(self())[p]
                count += 1
        return count
    
    def exportParams(self, params):
        """Export parameters to lmfit dictionary"""
        for p in self.__dict__.keys():
            params[p].value = self.__dict__[p]
            
    def printParams(self):
        for p in self.__dict__.keys():
            print(p,' = ',self.__dict__[p])
    
    def storeStates(self,soln,t):#,pulseInds):
        self.states = np.vstack((self.states, soln)) #np.append(self.states, soln, axis=0)
        self.t = np.hstack((self.t, t)) #np.append(self.t, t, axis=1)
        #self.pulseInd = np.append(self.pulseInd, pulseInds, axis=0)
    
    def getStates(self):
        """Returns states, t"""
        return self.states, self.t
    
    def reportState(self):
        self.dispRates()
        #print('phi = {:.3g}'.format(self.phi))
        #print('V = {:.3g}'.format(self.V))
    
    def initStates(self, phi, s0=None):
        """Clear state arrays and set transition rates"""
        if s0 is None:
            s0 = self.s_0
        assert(len(s0)==self.nStates)
        self.states = np.vstack((np.empty([0,self.nStates]),s0)) #np.empty([0,self.nStates])
        self.t = [0] #[]
        self.pulseInd = np.empty([0,2],dtype=int) # Light on and off indexes for each pulse
        self.setLight(phi)
        #if s0 is not None: # Override default initial conditions
        #    self.s_0 = s0
    
    def calcfV(self, V): 
        
        #if self.useIR:  # Optional model feature
        if self.v0 == 0:    ############################################################### Finish this! Generalise!!!
            raise ZeroDivisionError("f(V) undefined for v0 = 0")
        try:
            fV = (self.v1/(V-self.E))*(1-np.exp(-(V-self.E)/self.v0)) # Dimensionless
        except ZeroDivisionError:
            if np.isscalar(V):
                if (V == self.E):
                    fV = self.v1/self.v0
            else: #type(fV) in (tuple, list, array)
                fV[np.isnan(fV)] = self.v1/self.v0 # Fix the error when dividing by zero
        #else: 
        #    fV=1 ### Extend to vector
        return fV# * (V-self.E)
                
    def plotStates(self,t,states,pulses,labels,phiOn=0,peaks=[],name=None): ### Check how to check for optional arguments
        if len(peaks) > 0:
            plotPieCharts = True
        else:
            plotPieCharts = False
        
        figWidth, figHeight = mp.rcParams['figure.figsize']
        fig = plt.figure(figsize=(figWidth, 1.5*figHeight))
        #fig = plt.figure()
        gs = plt.GridSpec(3,3)
        
        totT = t[-1]
        
        # Plot line graph of states
        axLine = fig.add_subplot(gs[0,:])
        plt.plot(t,states)
        sig, = plt.plot(t, np.sum(states,axis=1), color='k', linestyle='--')
        plt.setp(axLine.get_xticklabels(), visible=False)
        plt.ylabel('$\mathrm{State\ occupancy}$')# proportion')
        labelsIncSum = np.append(labels,'$\Sigma s_i$')
        plt.legend(labelsIncSum,loc=6)
        plt.xlim((0,totT)) #plt.xlim((0,delD+(nPulses*(onD+offD)))) # t_run
        plt.ylim((-0.1,1.1))
        if addTitles:
            plt.title('$\mathrm{State\ variables\ through\ time}$') #plt.title('State variables through time: $v={} \mathrm{{mV}},\ \phi={:.3g} \mathrm{{photons}} \cdot \mathrm{{s}}^{{-1}} \cdot \mathrm{{cm}}^{{-2}}$'.format(V,phiOn))
        plotLight(pulses, axLine)

        
        ### Plot stack plot of state variables
        axStack = fig.add_subplot(gs[1,:], sharex=axLine)
        plt.stackplot(t,states.T)
        plt.ylim((0,1))
        plt.xlim((0,totT)) #plt.xlim((0,delD+(nPulses*(onD+offD))))
        plotLight(pulses, axStack, 'borders')
        if addTitles:
            axStack.title.set_visible(False)
        plt.xlabel('$\mathrm{Time\ [ms]}$')
        plt.ylabel('$\mathrm{State\ occupancy}$')# proportion')
        
        if plotPieCharts:
            axS0 = fig.add_subplot(gs[2,0])
            initialStates = self.s0 * 100
            #print(initialStates,labels)
            if verbose > 1:
                pct = {l:s for l,s in zip(labels,sizes)}
                print('Initial state occupancies (%):',sorted(pct.items(),key=lambda x: labels.index(x[0])))
            patches, texts, autotexts = plt.pie(initialStates, labels=labels, autopct='%1.1f%%', startangle=90, shadow=False) #, explode=explode
            for lab in range(len(labels)):
                texts[lab].set_fontsize(mp.rcParams['ytick.labelsize'])
                autotexts[lab].set_fontsize(mp.rcParams['axes.labelsize'])
            plt.axis('equal')
            if addTitles:
                plt.title('$\mathrm{Initial\ state\ occupancies}$')
            #else:
            #    plt.title('$t_{0}$')
            
            if peaks: ### Plot peak state proportions
                pInd = peaks[0] # Plot the first peak
                axLine.axvline(x=t[pInd],linestyle=':',color='k')
                axStack.axvline(x=t[pInd],linestyle=':',color='k')
                axPeak = fig.add_subplot(gs[2,1])
                sizes = states[pInd,:] * 100
                #sizes = [s*100 for s in sizes]
                #explode = (0,0,0.1,0.1,0,0)
                if verbose > 1:
                    pct = {l:s for l,s in zip(labels,sizes)}
                    print('Peak state occupancies (%):',sorted(pct.items(),key=lambda x: labels.index(x[0])))
                patches, texts, autotexts = plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, shadow=False)#, explode=explode)
                for lab in range(len(labels)):
                    texts[lab].set_fontsize(mp.rcParams['ytick.labelsize'])
                    autotexts[lab].set_fontsize(mp.rcParams['axes.labelsize'])
                plt.axis('equal')
                if addTitles:
                    plt.title('$\mathrm{Simulated\ peak\ state\ occupancies}$')
                #else:
                #    plt.title('$t_{peak}$')
            
            if phiOn > 0: ### Plot steady state proportions
                axSS = fig.add_subplot(gs[2,2])
                steadyStates = self.calcSteadyState(phiOn) * 100 # Convert array of proportions to %
                #steadyStates = [s*100 for s in steadyStates]
                #explode = (0,0,0.1,0.1,0,0)
                if verbose > 1:
                    pct = {l:s for l,s in zip(labels,sizes)}
                    print('Steady state occupancies (%):',sorted(pct.items(),key=lambda x: labels.index(x[0])))
                patches, texts, autotexts = plt.pie(steadyStates, labels=labels, autopct='%1.1f%%', startangle=90, shadow=False) #, explode=explode
                for lab in range(len(labels)):
                    texts[lab].set_fontsize(mp.rcParams['ytick.labelsize'])
                    autotexts[lab].set_fontsize(mp.rcParams['axes.labelsize'])
                plt.axis('equal')
                if addTitles:
                    plt.title('$\mathrm{Analytic\ steady\ state\ occupancies}$')
                #else:
                #    plt.title('$t_{\inf}$')

            

        plt.tight_layout()
        
        if name is not None:
            plt.savefig(fDir+name+'.'+saveFigFormat, format=saveFigFormat)


class RhO_3states(OGmodel):
    
    # Class attributes
    nStates = 3
    useAnalyticSoln = True
    labels = ['$C$','$O$','$D$']
    stateVars = ['C','O','D']
    s_0 = np.array([1,0,0])          # Default: Initialise in dark 
    phi_0 = 0.0
    #useIR = False
    connect = [[0,1,0],
               [0,0,1],
               [1,0,0]]
    conDir  = [[ 0,-1, 1],
               [ 1, 0,-1],
               [-1, 1, 0]]
    equations = """
                $$ \dot{C} = G_{r}(\phi)D - G_{a}(\phi)C $$
                $$ \dot{O} = G_{a}(\phi)C - G_{d}O $$
                $$ \dot{D} = G_{d}O - G_{r}(\phi)D $$
                $$ C + O + D = 1 $$
                $$ G_a(\phi) = k\\frac{\phi^p}{\phi^p + \phi_m^p} $$
                $$ G_r = G_{r0} + G_{r1}(\phi) $$
                $$ f(v) = \\frac{1-\\exp({-(v-E)/v_0})}{(v-E)/v_1} $$
                $$ I_{\phi} = g O f(v) (v-E) $$
                """
    #"""
    #\begin{align*}
    #\frac{dC}{dt} &= G_{r}D - P C
    #\frac{dO}{dt} &= P C -G_{d}O
    #\frac{dD}{dt} &= G_{d}O-G_{r}D
    #C+O+D &= 1
    #P &= \phi\frac{\epsilon \sigma_{ret}}{w_{loss}}
    #G_r &= G_{r,d} + \mathcal{H}(\phi) \cdot G_{r,l}
    #I_{\phi} &= \bar{g} O \cdot (v-E)
    #\end{align}
    #"""                
                
    eqIss = """$I_{SS} = \bar{g} \cdot \frac{P \cdot G_r}{G_d \cdot (G_r + P) + P \cdot G_r} \cdot (v-E) 
    = \bar{g} \cdot \frac{\tau_d}{\tau_d + \tau_r + \tau_\phi} \cdot (v-E)$"""
    
#     phi0 = 1e14 # Normalising light intensity parameter [photons * s^-1 * mm^-2] ~ 1/10 of threshold
    
    # Solver parameters
#     dt = 0.1 #0.01 #0.1 #0.001    
    
    def __init__(self, params=modelParams['3'], rhoType='Rhodopsin'): # E=0.0, #phi=0.0 RhO.setParams(d3sp)  # (self, E=0.0, rhoType='Rhodopsin')
        #self.equations = RhO_3states.equations
        self.rhoType = rhoType # E.g. 'ChR2' or 'ArchT'
        
        self.setParams(params)
        
        # Three-state model parameters
        #self.E = E                  # [mV]    Channel reversal potential
        #self.k = 8.2#1.64e-16 *1e18#8.2*(2e-14*1e-3) #0.5*1.2e-14/1.1    # [ms^-1] Quantum efficiency * number of photons absorbed by a RhO molecule per unit time
        #self.P = self.set_P(phi) # [ms^-1] Quantum efficiency * number of photons absorbed by a ChR2 molecule per unit time
        #self.Gd = 0.1 #0.117  #1/11              # [ms^-1] @ 1mW mm^-2
        #self.Gr0 = 1/5000 #Gr_dark = 1/5000       # [ms^-1] tau_r,dark = 5-10s p405 Nikolic et al. 2009
        #self.Gr1 = 0.016 #Gr_light = 0.016#1/165       # [ms^-1] (Gr,light @ 1mW mm^-2)
        #self.phi0 = 0.7e15#0.02/(2e-14*1e-3)
        #self.phiSat = 4e17#6.7e17 #13.6/(2e-14*1e-3)
        
        #self.g = 100e-3 * 1.67e5 *2   # [pS] g1 (100fS): Conductance of an individual ion channel * N (100000)
        
        #self.useIR = False # Implement rectifier!!!
        # Initial conditions: Instantaneous photon flux density = 0.0
        #self.s_0 = np.array([1,0,0])          # Initialise in dark 
        self.initStates(phi=self.phi_0, s0=self.s_0)        # Initialise in dark
        if verbose > 1:
            print("Nikolic et al. {}-state {} model initialised!".format(self.nStates,self.rhoType))
        
        if verbose > 1: 
            self.printParams()
    
    def reportParams(self): # Replace with local def __str__(self):
        report =  'Three-state model parameters\n'
        report += '============================\n'
        report += 'E    = {:12.3g}\n'.format(self.E)
        report += 'k    = {:12.3g}\n'.format(self.k)
        report += 'phim = {:12.3g}\n'.format(self.phim)
        report += 'p    = {:12.3g}\n'.format(self.p)
        report += 'Gd   = {:12.3g}\n'.format(self.Gd)
        report += 'Gr0  = {:12.3g}\n'.format(self.Gr0)
        report += 'Gr1  = {:12.3g}\n'.format(self.Gr1)
        report += 'g    = {:12.3g}\n'.format(self.g)
        report += '----------------------------'
        #print('Three-state model parameters')
        #print('============================')
        #print('|  E        = {:12.3g} |'.format(self.E))
        #print('|  k        = {:12.3g} |'.format(self.k))
        #print('|  Gd       = {:12.3g} |'.format(self.Gd))
        #print('|  Gr_dark  = {:12.3g} |'.format(self.Gr_dark))
        #print('|  Gr_light = {:12.3g} |'.format(self.Gr_light))
        #print('|  g        = {:12.3g} |'.format(self.g))
        #print('----------------------------')
        return report
        

    
    def set_P(self, phi):
        #return self.k * phi
        #return 0.5 * phi * (1.2e-8 * 1e-6) / 1.1  # eps * phi * sigma_ret (mm^-2) / wloss
        #return self.k * phi #(1 - np.exp(-phi/self.phiSat))
        return self.k * phi**self.p/(phi**self.p + self.phim**self.p)
    
    def set_Gr(self, phi):
        return self.Gr0 + (phi>0)*self.Gr1
        #return self.Gr0 + self.Gr1 * np.log(1 + phi/self.phi0) # self.Gr0 + self.Gr1
        #return self.Gr_dark + self.Gr_light * np.log(1 + phi/self.phi0) # self.Gr0 + self.Gr1
        # if phi>0:
            # return self.Gr_dark + self.Gr_light #*log(1 + phi/phi0)
        # else:
            # return self.Gr_dark
        # return 1/(taur_dark*exp(-log(1+phi/phi0))+taur_min) # Fig 6 Nikolic et al. 2009
        ### return Gr_dark + kr*(1-exp(-phi/phi0)) # a = Gr_max - Gr_dark
        
    #def set_Gd(self, phi):
    #    return 1/(taud_dark - a*log(1+phi/phi0)) # Fig 6 Nikolic et al. 2009
    
    def setLight(self, phi):
        """Set transition rates according to the instantaneous photon flux density"""
        #assert(phi >= 0)
        if phi < 0:
            phi = 0
        self.phi = phi
        self.P = self.set_P(phi)
        self.Gr = self.set_Gr(phi)
        if verbose > 1:
            self.dispRates()
    
    def dispRates(self):
        #print("Transition rates (phi={:.3g}): O <--[P={:.3g}]-- C <--[Gr={:.3g}]-- D".format(self.phi,self.P,self.Gr))
        #print(self.phi); print(type(self.phi))
        #print(self.P); print(type(self.P))
        #print(self.Gd); print(type(self.Gd))
        #print(self.Gr); print(type(self.Gr))
        print("Transition rates (phi={:.3g}): C --[P={:.3g}]--> O --[Gd={:.3g}]--> D --[Gr={:.3g}]--> C".format(self.phi,self.P,self.Gd,self.Gr))
    
    # def solveStates(self, s_0, t): # , phi e.g. f_phi(t) # http://stackoverflow.com/questions/5649313/a-possible-bug-in-odeint-interp1d-interplay
        # """Function describing the differential equations of the 3-state model to be solved by odeint"""
        # # Add interpolation of values for phi(t) to initialisation f_phi = interp1d(t,sin(w*t),kind='cubic')
        # # Then pass as an argument to integrator: odeint(func, y0, t, args=())
        # # self.setLight(f_phi(t))
        # C,O,D = s_0 # Split state vector into individual variables s1=s[0], s2=s[1], etc
        # f0 = -self.P*C +             self.Gr*D   # C'
        # f1 =  self.P*C - self.Gd*O               # O'
        # f2 =              self.Gd*O - self.Gr*D   # D'
        # #f2 = -(f0+f1)
        # return np.array([ f0, f1, f2 ])
    
    def solveStates(self, s_0, t, phi_t=None): # , phi e.g. f_phi(t) # solveStatesPhi_t http://stackoverflow.com/questions/5649313/a-possible-bug-in-odeint-interp1d-interplay
        """Function describing the differential equations of the 3-state model to be solved by odeint"""
        # Add interpolation of values for phi(t) to initialisation f_phi = interp1d(t,sin(w*t),kind='cubic')
        # Then pass as an argument to integrator: odeint(func, y0, t, args=())
        
        if phi_t is not None:
            self.setLight(float(phi_t(t)))
            #print("dydt: phi_t({})={}".format(t,phi_t(t)))
        C,O,D = s_0 # Split state vector into individual variables s1=s[0], s2=s[1], etc
        f0 = -self.P*C +             self.Gr*D   # C'
        f1 =  self.P*C - self.Gd*O               # O'
        f2 =             self.Gd*O - self.Gr*D   # D'
        #f2 = -(f0+f1)
        return np.array([ f0, f1, f2 ])
    
    # def jacobian(self, s_0, t):
        # # Jacobian matrix used to improve precision / speed up ODE solver
        # # jac[i,j] = df[i]/dy[j]; where y'(t) = f(t,y)
        # return np.array([[-self.P, 0, self.Gr],
                         # [self.P, -self.Gd, 0],
                         # [0, self.Gd, -self.Gr]])
    
    def jacobian(self, s_0, t, phi_t=None): # jacobianPhi_t
        #print("Jac: phi_t({})={}".format(t,phi_t(t)))
        #self.setLight(phi_t(t))
        # Jacobian matrix used to improve precision / speed up ODE solver
        # jac[i,j] = df[i]/dy[j]; where y'(t) = f(t,y)
        return np.array([[-self.P, 0, self.Gr],
                         [self.P, -self.Gd, 0],
                         [0, self.Gd, -self.Gr]])
    
    # def hessian(self, s_0, t):
        # Hessian matrix for scipy.optimize.minimize (Only for Newton-CG, dogleg, trust-ncg.)
        # H(f)_ij(X) = D_iD_jf(X)
        # return np.array([[0, 0, 0],
        #                 [0, 0, 0],
        #                 [0, 0, 0]])
    
    def calcI(self, V, states=None):
        """Calculate the photocurrent from the cell membrane voltage and state matrix"""
        ### if useInwardRect: ... else: fV=1
        if states is None:
            states = self.states
        O = states[:,1] # time x C,O,D
        I_RhO = self.g*O*self.calcfV(V)*(V-self.E)
        return I_RhO * 1e-6 # pS * mV * 1e-6 = nA
    
    def calcPsi(self, states):
        return 1
    
    def calcOn(self,t):
        """Calculate the on phase current for square light pulses from the analytic solution"""
        r = np.array([lam1, lam2])
        k = np.array([a1, a2])
        I = k * np.exp(-r*t)
        -(a0 + a1*(1-np.exp(-t/tau_act)) + a2*np.exp(-t/tau_deact))
        pass
    
    def calOff():
        """Calculate the off phase current for square light pulses from the analytic solution"""
        -(A*np.exp(-Gd*t))
        pass
    
    def calcSteadyState(self, phi):
        self.setLight(phi)
        denom3 = self.Gd * (self.Gr + self.P) + self.P * self.Gr
        Cs = self.Gd*self.Gr/denom3
        Os = self.P*self.Gr/denom3
        Ds = self.P*self.Gd/denom3
        self.steadyStates = np.array([Cs, Os, Ds])
        return np.array([Cs, Os, Ds])
    
    def calcSoln(self, t, s0=[1,0,0]): #RhO_3states.s_0
        [C_0, O_0, D_0] = s0
        P = self.P
        Gd = self.Gd
        Gr = self.Gr
        #if t[0] > 0: # Shift time array to start at 0
        t = t - t[0] # Shift time array forwards or backwards to start at 0
        
        SP = P*Gd + P*Gr + Gd*Gr
        SQ = P**2 + Gd**2 + Gr**2
        if 2*SP > SQ:
            print('Imaginary solution! SP = {}; SQ = {} --> (SQ-2*SP)**(1/2) = NaN'.format(SP, SQ))
            #raise ValueError() # Uncomment this when error catching is implemented
        #else:
        RSD = (SQ-2*SP)**(1/2) # xi
        lambda_1 = (P + Gd + Gr + RSD)/2
        lambda_2 = (P + Gd + Gr - RSD)/2
        Z_1 = C_0*Gd*P + O_0*(Gd*(P - lambda_1)) + D_0*Gr*(Gr-lambda_2)
        Z_2 = C_0*Gd*P + O_0*(Gd*(P - lambda_2)) + D_0*Gr*(Gr-lambda_1)
        Exp_1 = np.exp(-t*lambda_1)
        Exp_2 = np.exp(-t*lambda_2)
        
        # print(SP)
        # print(SQ)
        # print(RSD)
        # print(lambda_1)
        # print(lambda_2)
        # print(Z_1)
        # print(Z_2)
        # print(Exp_1)
        # print(Exp_2)
        
        C = (Z_1*lambda_2*(lambda_1-Gd-Gr)*Exp_1 - Z_2*lambda_1*(lambda_2-Gd-Gr)*Exp_2 + (RSD*Gd**2*Gr*(C_0+D_0+O_0)))/(Gd*SP*RSD)
        O = (-Z_1*lambda_2*(lambda_1-Gr)*Exp_1 + Z_2*lambda_1*(lambda_2-Gr)*Exp_2 + (RSD*P*Gd*Gr*(C_0+D_0+O_0)))/(Gd*SP*RSD)
        D = (Z_1*lambda_2*Exp_1 - Z_2*lambda_1*Exp_2 + (RSD*Gd*P*(C_0+D_0+O_0)))/(SP*RSD)
        
        return np.column_stack((C,O,D)) #np.row_stack((C,O,D)).T #np.column_stack((C.T,O.T,D.T))
        
    # def calcSoln(self, t, s0=[1,0,0]):
        # [C_0,O_0,D_0] = s0
        # P = self.P
        # Gd = self.Gd
        # Gr = self.Gr
        # #if t[0] > 0: # Shift time array to start at 0
        # t = t - t[0] # Shift time array forwards or backwards to start at 0
        
        
        # SP = P*Gd + P*Gr + Gd*Gr
        # SQ = P**2 + Gd**2 + Gr**2
        # lambda_1 = (Gd + Gr + P + (SQ-2*SP)**(1/2))/2
        # lambda_2 = (Gd + Gr + P - (SQ-2*SP)**(1/2))/2
        # Den_1 = (2*SP*(SQ-2*SP)**(1/2))
        # Fac_1 = (C_0*Gd*P**2 + C_0*Gd**2*P + Gd*Gr**2*D_0 - Gd**2*Gr*D_0 - 2*Gd**2*Gr*O_0 - Gr*D_0*P**2 + Gr**2*D_0*P + Gd*O_0*P**2 - Gd**2*O_0*P + C_0*Gd*Gr*P - Gd*Gr*O_0*P - C_0*Gd*P*(SQ-2*SP)**(1/2) + Gd*Gr*D_0*(SQ-2*SP)**(1/2) + Gr*D_0*P*(SQ-2*SP)**(1/2) - Gd*O_0*P*(SQ-2*SP)**(1/2))
        # Fac_2 = (C_0*Gd*P**2 + C_0*Gd**2*P + Gd*Gr**2*D_0 - Gd**2*Gr*D_0 - 2*Gd**2*Gr*O_0 - Gr*D_0*P**2 + Gr**2*D_0*P + Gd*O_0*P**2 - Gd**2*O_0*P + C_0*Gd*Gr*P - Gd*Gr*O_0*P + C_0*Gd*P*(SQ-2*SP)**(1/2) - Gd*Gr*D_0*(SQ-2*SP)**(1/2) - Gr*D_0*P*(SQ-2*SP)**(1/2) + Gd*O_0*P*(SQ-2*SP)**(1/2))
    
        # C = (np.exp(-t*lambda_1)*np.exp(-t*lambda_2)*((P*np.exp(t*lambda_2)*Fac_1)/(2*(SP)) + (P*np.exp(t*lambda_1)*Fac_2)/(2*(SP)) + (P**2*np.exp(t*lambda_2)*Fac_1)/(2*(SP)*(SQ-2*SP)**(1/2)) - (P**2*np.exp(t*lambda_1)*Fac_2)/(2*(SP)*(SQ-2*SP)**(1/2)) - (Gd*P*np.exp(t*lambda_2)*Fac_1)/(2*(SP)*(SQ-2*SP)**(1/2)) - (Gr*P*np.exp(t*lambda_2)*Fac_1)/(2*(SP)*(SQ-2*SP)**(1/2)) + (Gd*P*np.exp(t*lambda_1)*Fac_2)/(2*(SP)*(SQ-2*SP)**(1/2)) + (Gr*P*np.exp(t*lambda_1)*Fac_2)/(2*(SP)*(SQ-2*SP)**(1/2)) + (2*Gd**2*Gr*P*np.exp(t*lambda_1)*np.exp(t*lambda_2)*(C_0 + D_0 + O_0))/(SP)))/(2*Gd*P)
        
        # O = -(np.exp(-t*lambda_1)*np.exp(-t*lambda_2)*((np.exp(t*lambda_1)*Fac_2)/(2*(SP)) + (np.exp(t*lambda_2)*Fac_1)/(2*(SP)) - (Gd*np.exp(t*lambda_1)*Fac_2)/(2*(SP)*(SQ-2*SP)**(1/2)) + (Gr*np.exp(t*lambda_1)*Fac_2)/(2*(SP)*(SQ-2*SP)**(1/2)) - (P*np.exp(t*lambda_1)*Fac_2)/(2*(SP)*(SQ-2*SP)**(1/2)) + (Gd*np.exp(t*lambda_2)*Fac_1)/(2*(SP)*(SQ-2*SP)**(1/2)) - (Gr*np.exp(t*lambda_2)*Fac_1)/(2*(SP)*(SQ-2*SP)**(1/2)) + (P*np.exp(t*lambda_2)*Fac_1)/(2*(SP)*(SQ-2*SP)**(1/2)) - (2*Gd*Gr*P*np.exp(t*lambda_1)*np.exp(t*lambda_2)*(C_0 + D_0 + O_0))/(SP)))/(2*Gd)
        
        # D = np.exp(-t*lambda_1)*np.exp(-t*lambda_2)*((np.exp(t*lambda_2)*Fac_1)/(2*(SP)*(SQ-2*SP)**(1/2)) - (np.exp(t*lambda_1)*Fac_2)/(2*(SP)*(SQ-2*SP)**(1/2)) + (Gd*P*np.exp(t*lambda_1)*np.exp(t*lambda_2)*(C_0 + D_0 + O_0))/(SP))
        
        # return np.row_stack((C,O,D)).T #np.column_stack((C.T,O.T,D.T))


class RhO_4states(OGmodel):
    
    # Class attributes
    nStates = 4
    useAnalyticSoln = False
    labels = ['$C_1$','$O_1$','$O_2$','$C_2$']
    stateVars = ['C1','O1','O2','C2']
    s_0 = np.array([1,0,0,0])       # Default: Initialise in the dark
    phi_0 = 0.0  # Instantaneous Light flux
    #useIR = False
    connect = [[0,1,0,0],
               [1,0,1,0],
               [0,1,0,1],
               [1,0,1,0]]
    
    equations = """
                $$ \dot{C_{\\alpha}} = G_{r}C_{\\beta} + G_{d{\\alpha}}O_{\\alpha} - G_{a{\\alpha}}(\phi)C_{\\alpha} $$
                $$ \dot{O_{\\alpha}} = G_{a{\\alpha}}(\phi)C_{\\alpha} - (G_{d{\\alpha}}+G_{f}(\phi))O_{\\alpha} + G_{b}(\phi)O_{\\beta} $$
                $$ \dot{O_{\\beta}} = G_{a{\\beta}}(\phi)C_{\\beta} + G_{f}(\phi)O_{\\alpha} - (G_{d{\\beta}}+G_{b}(\phi))O_{\\beta} $$
                $$ \dot{C_{\\beta}} = G_{d{\\beta}}O_{\\beta} - (G_{a{\\beta}}(\phi)+G_{r0})C_{\\beta} $$
                $$ C_{\\alpha} + O_{\\alpha} + O_{\\beta} + C_{\\beta} = 1 $$
                $$$$
                $$ G_{a{\\alpha}}(\phi) = k_{\\alpha}\\frac{\phi^p}{\phi^p + \phi_m^p} $$
                $$ G_{a{\\beta}}(\phi) = k_{\\beta}\\frac{\phi^p}{\phi^p + \phi_m^p} $$
                $$ G_{f}(\phi) = G_{f0} + k_{f} \\frac{\phi^q}{\phi^q + \phi_m^q} $$
                $$ G_{b}(\phi) = G_{b0} + k_{b} \\frac{\phi^q}{\phi^q + \phi_m^q} $$
                $$$$
                $$ f(v) = \\frac{1-\\exp({-(v-E)/v_0})}{(v-E)/v_1} $$
                $$ I_{\phi} = g (O_{\\alpha}+\gamma O_{\\beta}) f(v) (v-E) $$
                """     
    
    #phi = 0.0  # Instantaneous Light flux
#     phi0 = 1e14 # Normalising light intensity parameter [photons * s^-1 * mm^-2] ~ 1/10 of threshold
    
    ###### gam = 0.1
    
    # Solver parameters
#     dt = 0.1 #0.01 #0.1 #0.001
    
    def __init__(self, params=modelParams['4'], rhoType='Rhodopsin'): #E=0.0, gam=0.05, phi0=1e14, #, A=31192)
        
        self.rhoType = rhoType # E.g. 'ChR2' or 'ArchT'
    
        self.setParams(params)
        # Four-state model parameters
        #self.E = E                  # [mV]      Channel reversal potential
        #self.gam = gam              # []        Ratio of single channel conductances: O2/O1
        #self.phi0 = phi0            # [photons * s^-1 * mm^-2] Normalising photon flux density ~ 1/10 of threshold
        ##self.A = A                  # [um^2]  Effective area of the cell / compartment
        #self.sigma_ret = 1.2e-8 * 1e-6 # Convert from m^2 to mm^2
        #self.w_loss = 1.1
        #self.k1 = 0.5 * self.sigma_ret / self.w_loss # Quantum efficiency * sigma_ret / w_loss
        #self.k2 = 0.15 * self.sigma_ret / self.w_loss # Quantum efficiency * sigma_ret / w_loss
        #self.Gr = 0.000400 # [ms^-1] ==> tau_r = 2.5s
        #self.Gd1 = 0.11 # [ms^-1]
        #self.Gd2 = 0.025 # [ms^-1]
        #self.c1 = 0.03
        #self.c2 = 0.0115
        #self.e12d = 0.01 # [ms^-1]
        #self.e21d = 0.015 # [ms^-1]
        #self.g = 100e-3 * 1.67e5   # [pS] g1 (100fS): Conductance of an individual ion channel * N (~150000)
        
        #self.useInwardRect = False # Implement rectifier!!!
        # Initial conditions
        #self.s_0 = np.array([1,0,0,0])
        self.initStates(phi=self.phi_0, s0=self.s_0) # phi
        if verbose > 1:
            print("Nikolic et al. {}-state {} model initialised!".format(self.nStates,self.rhoType))
        
        if verbose > 1: 
            self.printParams()
    
    def reportParams(self): # Replace with local def __str__(self):
        report =  'Four-state model parameters\n'
        report += '===========================\n'
        report += 'E    = {:12.3g}\n'.format(self.E)
        report += 'gam  = {:12.3g}\n'.format(self.gam)
        report += 'phi0 = {:12.3g}\n'.format(self.phi0)
        report += 'k1   = {:12.3g}\n'.format(self.k1)
        report += 'k2   = {:12.3g}\n'.format(self.k2)
        report += 'phim = {:12.3g}\n'.format(self.phim)
        report += 'p    = {:12.3g}\n'.format(self.p)
        report += 'Gr   = {:12.3g}\n'.format(self.Gr)
        report += 'Gd1  = {:12.3g}\n'.format(self.Gd1)
        report += 'Gd2  = {:12.3g}\n'.format(self.Gd2)
        report += 'c1   = {:12.3g}\n'.format(self.c1)
        report += 'c2   = {:12.3g}\n'.format(self.c2)
        report += 'e12d = {:12.3g}\n'.format(self.e12d)
        report += 'e21d = {:12.3g}\n'.format(self.e21d)
        report += 'g    = {:12.3g}\n'.format(self.g)
        report += '---------------------------'
        return report
    
    def set_Ga1(self, phi):
        # N.B. making Ga a function of time (as in Appendix 1) results in the Six-state model
        # Gai = ei * F * f(t,tChR) See App 1
        # Ga = 1/tauChR
        #e = 0.5
        #sigma_ret = 1.2e-8 * 1e-6 # Convert from m^2 to mm^2
        #w_loss = 1.1
        #return self.k1 * phi/self.phi0 #e*phi*sigma_ret / w_loss
        #return self.k1 * (1-np.exp(-phi/self.phi0)) #e*phi*sigma_ret / w_loss
        return self.k1 * phi**self.p/(phi**self.p + self.phim**self.p)
    
    def set_Ga2(self, phi):
        #e = 0.15
        #sigma_ret = 1.2e-8  * 1e-6 # Convert from m^2 to mm^2
        #w_loss = 1.1
        #return self.k2 * phi/self.phi0 #e*phi*sigma_ret / w_loss
        #return self.k2 * (1-np.exp(-phi/self.phi0))
        return self.k2 * phi**self.p/(phi**self.p + self.phim**self.p)
    
    def set_e12(self, phi):
        #return self.e12d + self.c1*np.log(1+(phi/self.phi0)) # e12(phi=0) = e12d
        return self.e12d + self.c1 * phi**self.q/(phi**self.q + self.phim**self.q)

    def set_e21(self, phi):
        #return self.e21d + self.c2*np.log(1+(phi/self.phi0)) # e21(phi=0) = e21d
        return self.e21d + self.c2 * phi**self.q/(phi**self.q + self.phim**self.q)

    def setLight(self, phi):
        """Set transition rates according to the instantaneous photon flux density"""
        #assert(phi >= 0)
        if phi < 0:
            phi = 0
        self.phi = phi
        self.Ga1 = self.set_Ga1(phi)
        self.Ga2 = self.set_Ga2(phi)
        self.e12 = self.set_e12(phi)
        self.e21 = self.set_e21(phi)
        if verbose > 1:
            self.dispRates()
            
    def dispRates(self):
        print("Transition rates (phi={:.3g}): C1 --[Ga1={:.3g}]--> O1 --[e12={:.3g}]--> O2".format(self.phi,self.Ga1,self.e12))
        print("Transition rates (phi={:.3g}): O1 <--[e21={:.3g}]-- O2 <--[Ga2={:.3g}]-- C2".format(self.phi,self.e21,self.Ga2))
    
    def solveStates(self, s_0, t, phi_t=None):
        """Function describing the differential equations of the 4-state model to be solved by odeint"""
        if phi_t is not None:
            self.setLight(float(phi_t(t)))
        C1,O1,O2,C2 = s_0 # Split state vector into individual variables s1=s[0], s2=s[1], etc
        f0 = -self.Ga1*C1   +       self.Gd1*O1     +                       self.Gr *C2 # C1'
        f1 =  self.Ga1*C1 - (self.Gd1+self.e12)*O1  +   self.e21*O2                     # O1'
        f2 =                        self.e12*O1 - (self.Gd2+self.e21)*O2 +  self.Ga2*C2 # O2'
        f3 =                                        self.Gd2*O2 - (self.Ga2+self.Gr)*C2 # C2'
        #f3 = -(f0+f1+f2)
        return np.array([ f0, f1, f2, f3 ])
    
    def jacobian(self, s_0, t, phi_t=None):
        # Jacobian matrix used to improve precision / speed up ODE solver
        # jac[i,j] = df[i]/dy[j]; where y'(t) = f(t,y)
        return np.array([[-self.Ga1, self.Gd1, 0, self.Gr],
                         [self.Ga1, -(self.Gd1+self.e12), self.e21, 0],
                         [0, self.e12, -(self.Gd2+self.e21), self.Ga2],
                         [0, 0, self.Gd2, -(self.Ga2+self.Gr)]])
    
    def calcI(self, V, states=None):
        if states is None:
            states = self.states
        O1 = states[:,1]
        O2 = states[:,2]
        I_RhO = self.g*(O1 + self.gam*O2)*self.calcfV(V)*(V-self.E)
        return I_RhO * 1e-6 # pS * mV * 1e-6 = nA
    
    def calcPsi(self, states):
        C1, O1, O2, C2 = states
        return O1 + self.gam * O2
    
    # def calcfV(self, V):
        # return 1
    
    def calcSteadyState(self, phi):
        self.setLight(phi)
        Ga1 = self.Ga1
        Ga2 = self.Ga2
        Gr = self.Gr
        Gd1 = self.Gd1
        Gd2 = self.Gd2
        e12 = self.e12
        e21 = self.e21
        denom4 = Ga1 * (e12 * (Gr + Gd2 + Ga2) + e21 * (Gr + Ga2) + Gd2 * Gr) + Gd1 * (e21 * (Gr + Ga2) + Gd2 * Gr) + e12 * Gd2 * Gr
        C1s = (Gd1 * (e21 * (Gr + Ga2) + Gd2 * Gr) + e12 * Gd2 * Gr) / denom4
        O1s = (Ga1 * (e21 * (Gr + Ga2) + Gd2 * Gr)) / denom4
        O2s = (e12 * Ga1 * (Gr + Ga2)) / denom4
        C2s = (e12 * Ga1 * Gd2) / denom4
        self.steadyStates = np.array([C1s, O1s, O2s, C2s])
        return np.array([C1s, O1s, O2s, C2s])

    def calcSoln(self, t, s0=[1,0,0,0]):
        raise NotImplementedError(self.nStates)

    
class RhO_6states(OGmodel):
    
    # Class attributes
    nStates = 6
    useAnalyticSoln = False
    #labels = ['$s_1$','$s_2$','$s_3$','$s_4$','$s_5$','$s_6$']
    labels = ['$C_1$','$I_1$','$O_1$','$O_2$','$I_2$','$C_2$']
    # stateVars = ['s1','s2','s3','s4','s5','s6'] # 
    stateVars = ['C1','I1','O1','O2','I2','C2'] #['C1','I1','O1','O2','I2','C2']
    s_0 = np.array([1,0,0,0,0,0])  # [s1_0=1, s2_0=0, s3_0=0, s4_0=0, s5_0=0, s6_0=0] # array not necessary
    phi_0 = 0.0     # Default initial flux
    #useIR = True
    connect = [[0,1,0,0,0,0], # s_1 --> s_i=1...6
               [0,0,1,0,0,0], # s_2 -->
               [1,0,0,1,0,0],
               [0,0,1,0,0,1],
               [0,0,0,1,0,0],
               [1,0,0,0,1,0]]
    
    
    equations = """
                $$ \dot{C_1} = -G_{a1}(\phi)C_1 + G_{d1}O_1 + G_{r0}C_2 $$
                $$ \dot{I_1} = G_{a1}(\phi)C_1 - G_{o1}I_1 $$
                $$ \dot{O_1} = G_{o1}I_1 - (G_{d1} + G_{f}(\phi))O_1 + G_{b}(\phi)O_2 $$
                $$ \dot{O_2} = G_{f}(\phi)O_1 - (G_{b}(\phi) + G_{d2})O_2 + G_{o2}I_2 $$
                $$ \dot{I_2} = -G_{o2}I_2 + G_{a2}(\phi)C_2 $$
                $$ \dot{C_2} = G_{d2}O_2 - (G_{a2}(\phi)+G_{r0})C_2 $$
                $$ C_1 + I_1 + O_1 + O_2 + I_2 + C_2 = 1 $$
                $$$$
                $$ G_{a1}(\phi) = k_{1} \\frac{\phi^p}{\phi^p + \phi_m^p} $$
                $$ G_{f}(\phi) = G_{f0} + k_{f} \\frac{\phi^q}{\phi^q + \phi_m^q} $$
                $$ G_{b}(\phi) = G_{b0} + k_{b} \\frac{\phi^q}{\phi^q + \phi_m^q} $$
                $$ G_{a2}(\phi) = k_{2} \\frac{\phi^p}{\phi^p + \phi_m^p} $$
                $$$$
                $$ f(v) = \\frac{1-\\exp({-(v-E)/v_0})}{(v-E)/v_1} $$
                $$ I_{\phi} = g (O_1+\gamma O_2) f(v)(v-E) $$
                """    
    
#     phi = 0.0  # Instantaneous Light flux
#     phi0 = 1e14 # Normalising light intensity parameter [photons * s^-1 * mm^-2] ~ 1/10 of threshold
    
    # Solver parameters
#     dt = 0.1 #0.01 #0.1 #0.001
    
    def __init__(self, params=modelParams['6'], rhoType='Rhodopsin'): # E=0.0, gam=0.05, phi0=1e14, A=3.12e4# phi=0.0
        
        self.rhoType = rhoType # E.g. 'ChR2' or 'ArchT'
        
        self.setParams(params)
        #self.g = self.gbar * self.A # [pS]      Total conductance
        
        ### Model constants
        #self.E = E                  # [mV]    Channel reversal potential
        #self.gam = gam              # []      Ratio of single channel conductances: O2/O1
        #self.phi0 = phi0            # [photons * s^-1 * mm^-2] Normalising photon flux density ~ 1/10 of threshold
        #self.A = A                  # [um^2]  Effective area of the cell / compartment
        #self.v0 = 43  # (mV)
        #self.v1 = 4.1 # (mV) #-4.1 Changed to correct f(v) but preserve the form of the numerator
        #self.gbar = 2.4 # (pS * um^-2)
        # gam = 0.05 # (Dimensionless)
        # A = 31192#e-6 # (um^2)
        # E = 0 # 0:8 (mV) 0e-3
        #self.g = self.gbar * self.A # [pS]      Total conductance
        
        #self.a10 = 5
        #self.a2 = 1
        #self.a30 = 0.022
        #self.a31 = 0.0135
        #self.a4 = 0.025
        #self.a6 = 0.00033   # = 1/tau6, tau6 = 3s = 3000ms
        #self.b1 = 0.13
        #self.b20 = 0.011
        #self.b21 = 0.0048
        #self.b3 = 1
        #self.b40 = 1.1
        
        #self.useIR = True
        
        # Initial conditions
        #self.s_0 = np.array([1,0,0,0,0,0])  # [s1_0=1, s2_0=0, s3_0=0, s4_0=0, s5_0=0, s6_0=0] # array not necessary
        self.initStates(phi=self.phi_0, s0=self.s_0) # phi
        if verbose > 1:
            print("Grossman et al. {}-state {} model initialised!".format(self.nStates,self.rhoType))
        
        if verbose > 1: 
            self.printParams()
    
    def set_a1(self,phi):
        #return self.a10*(phi/self.phi0)
        return self.a10 * phi**self.p/(phi**self.p + self.phim**self.p)

    def set_a3(self,phi):
        #return self.a30 + self.a31*np.log(1+(phi/self.phi0))
        return self.a30 + self.a31 * phi**self.q/(phi**self.q + self.phim**self.q)

    def set_b2(self,phi):
        #return self.b20 + self.b21*np.log(1+(phi/self.phi0))
        return self.b20 + self.b21 * phi**self.q/(phi**self.q + self.phim**self.q)

    def set_b4(self,phi):
        #return self.b40*(phi/self.phi0)
        return self.b40 * phi**self.p/(phi**self.p + self.phim**self.p)

    def setLight(self,phi):
        #assert(phi >= 0)
        if phi < 0:
            phi = 0
        self.phi = phi
        self.a1 = self.set_a1(phi)
        self.a3 = self.set_a3(phi)
        self.b2 = self.set_b2(phi)
        self.b4 = self.set_b4(phi)
        if verbose > 1:
            self.dispRates()
        
    def dispRates(self):
        print("Transition rates (phi={:.3g}): s3 --[a3]--> s4 = {}; s3 <--[b2]-- s4 = {}".format(self.phi,self.a3,self.b2))
        print("                  ^s2      s5^")
        print("                   \        /")
        print("                   [a1]   [b4]")
        print("                     \    /")
        print("                     s1  s6")
        print("Transition rates [a1] = {}; [b4] = {}".format(self.a1,self.b4))
    
    def solveStates(self, s_0, t, phi_t=None):
        """Function describing the differential equations of the 6-state model to be solved by odeint"""
        if phi_t is not None:
            self.setLight(float(phi_t(t)))
        s1,s2,s3,s4,s5,s6 = s_0 # Split state vector into individual variables s1=s[0], s2=s[1], etc
        d0 = -self.a1*s1 + self.b1*s3 + self.a6*s6           # s1'
        d1 =  self.a1*s1 - self.a2*s2                        # s2'
        d2 =  self.a2*s2 - (self.b1+self.a3)*s3 + self.b2*s4 # s3'
        d3 =  self.a3*s3 - (self.b2+self.a4)*s4 + self.b3*s5 # s4'
        d4 = -self.b3*s5 + self.b4*s6                        # s5'
        d5 =  self.a4*s4 - (self.b4+self.a6)*s6              # s6'
        #d5 = - (f0+f1+f2+f3+f4)
        #dr0 = -2*pi*f*sin(2*pi*f*t)*C(1+cos(2*pi*f*t))      # d/dt (A(1+cos(2*pi*f*t)))
        return np.array([ d0, d1, d2, d3, d4, d5 ])

    def jacobian(self, s_0, t, phi_t=None):
        return np.array([[-self.a1, 0, self.b1, 0, 0, self.a6],
                         [self.a1, -self.a2, 0, 0, 0, 0],
                         [0, self.a2, -(self.b1+self.a3), self.b2, 0, 0],
                         [0, 0, self.a3, -(self.b2+self.a4), self.b3, 0],
                         [0, 0, 0, 0, -self.b3, self.b4],
                         [0, 0, 0, self.a4, 0, -(self.b4+self.a6)]])
        
    def calcI(self, V, states=None): # Change to (V, psi)?
        """Takes Voltage [mV] and state variables s_3 and s_4 to calculate current [nA]
        By convention, positive ions entering the cell --> negative current (e.g. Na^+ influx). 
        Conversely, Positive ions leaving (or negative ions entering) the cell --> positive current (e.g. Cl^- in or K^+ out). """
        if states is None:
            states = self.states
        s3 = states[:,2] # O1
        s4 = states[:,3] # O2
        psi = s3 + (self.gam * s4) # Dimensionless
        ### if useInwardRect: ... else: fV=1
        # try:
            # fV = (self.v1/(V-self.E))*(1-np.exp(-(V-self.E)/self.v0)) # Dimensionless
        # except ZeroDivisionError:
            # if np.isscalar(V):
                # if (V == self.E):
                    # fV = self.v1/self.v0
            # else: #type(fV) in (tuple, list, array)
                # fV[np.isnan(fV)] = self.v1/self.v0 # Fix the error when dividing by zero
        g_RhO = self.g * psi #* fV # self.gbar * self.A # Conductance (pS * um^-2)
        I_RhO =  g_RhO * self.calcfV(V) * (V - self.E) # Photocurrent: (pS * mV)
        return I_RhO * (1e-6) # 10^-12 * 10^-3 * 10^-6 (nA)
    
##############################################################    
    def rectifierifier(V): ##### Redundant
        if self.v0 == 0:
            #print("f(V) undefined for v0 = 0")
            warnings.warn("f(V) undefined for v0 = 0")
        try:
            fV = (self.v1/(V-self.E))*(1-np.exp(-(V-self.E)/self.v0)) # Dimensionless
        except ZeroDivisionError:
            pass
        fV = (self.v1/(V-self.E))*(1-np.exp(-(V-self.E)/self.v0)) # Dimensionless
        if np.isscalar(fV):
            if (V == self.E):
                fV = self.v1/self.v0
        else: #type(fV) in (tuple, list, array)
            fV[np.isnan(fV)] = self.v1/self.v0 # Fix the error when dividing by zero

        return fV
    
    def equalFloats(x,y,eps=1e-6):
        diff = np.abs(x-y)
        if (x == y): # Catch infinities
            return True
        elif (x == 0 or y == 0 or diff < floatmin): # Either one number is 0 or both are very close
            return diff < (eps * floatmin)
        else: # Use relative error
            return diff / (np.abs(x) + np.abs(y)) < eps
#############################################################
        
    def calcSteadyState(self,phi): # implicitly depends on phi0
        self.setLight(phi)
        a1 = self.a1
        a2 = self.a2
        a3 = self.a3
        a4 = self.a4
        a6 = self.a6
        b1 = self.b1
        b2 = self.b2
        b3 = self.b3
        b4 = self.b4
        denom6 = (a1*a2*(a3*(b3*(b4+a4)+a4*b4)+b2*b3*b4)+b1*(a2*b2*b3*b4+a1*b2*b3*b4+a6*(a2*(b2*b3+a4*b3)+a1*(b2*b3+a4*b3)))+a6*(a1*(a2*(b2*b3+a4*b3+a3*b3)+a3*a4*b3)+a2*a3*a4*b3))
        s1s = (b1*(a2*b2*b3*b4 + a2*a6*(b2*b3 + a4*b3)) + a2*a3*a4*a6*b3)/denom6
        s2s = (b1*(a1*b2*b3*b4 + a1*a6*(b2*b3 + a4*b3)) + a1*a3*a4*a6*b3)/denom6
        s3s = (a1*a2*b2*b3*b4 + a1*a2*a6*(b2*b3 + a4*b3))/denom6
        s4s = (a1*a2*a3*b3*b4 + a1*a2*a3*a6*b3)/denom6
        s5s = (a1*a2*a3*a4*b4)/denom6
        s6s = (a1*a2*a3*a4*b3)/denom6
        self.steadyStates = np.array([s1s, s2s, s3s, s4s, s5s, s6s])
        return np.array([s1s, s2s, s3s, s4s, s5s, s6s])
    
    def calcPsi(self, states):
        s1,s2,s3,s4,s5,s6 = states
        return s3 + self.gam * s4
        
    def calcSoln(self, t, s0=[1,0,0,0,0,0]):
        raise NotImplementedError(self.nStates)
        
from collections import OrderedDict
models = OrderedDict([('3', RhO_3states), ('4', RhO_4states), ('6', RhO_6states)])#{'3': RhO_3states, '4': RhO_4states, '6': RhO_6states} # OrderedDict...
