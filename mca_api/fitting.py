import numpy as np
from scipy.special import erf
import uncertainties as uc
import warnings
from scipy.optimize import curve_fit, OptimizeWarning

class DummyCalibration:
    def applyToValue(self, value):
        return value
    
    def applyToDistance(self, dist):
        return dist

class FitInfo():
    def __init__(self, fit_type = 0, fit_range = [1,100], record_info = None, cutoff = 10):
        self.fit_type = fit_type
        self.fit_range = fit_range
        self.record_info = record_info
        self.cutoff = cutoff
        self.popt = None
        self.pcov = None
        self.chi_squared = 0
        self.red_chi_squared = 0
        self.dof = 0
        self._f = None
        self._p0ext = None
        self.fitted = False
        if self.fit_type == 1:
            # Gaussian
            self._f = gauss
            self._p0ext = []
        elif self.fit_type == 2:
            # Gaussian + const.
            self._f = gauss_const
            self._p0ext = [0]
        elif self.fit_type == 3:
            # Gaussian + lin.
            self._f = gauss_lin
            self._p0ext = [0,0]
        else:
            print("Invalid Fitting State in FitInfo.__init__:",self.fit_type)
    
    def run(self):
        events = self.record_info.events
        centers = self.record_info.centers

        # Fit Range
        events  =  events[self.fit_range[0]:self.fit_range[1]]
        centers = centers[self.fit_range[0]:self.fit_range[1]]

        self.popt, self.pcov, self.chisq, self.red_chisq, self.dof = curve_fit_general_gauss(centers, events, self.cutoff, self._f, self._p0ext)

    def get_parameters(self, calibration=DummyCalibration()):
        if self.pcov is None:
            return {"No":("Result", "")}
        elif isinstance(self.pcov,dict):
            return self.pcov
        
        perr = np.sqrt(np.diag(self.pcov))
        dict_params = {}
        if self.fit_type == 1:
            # Gaussian
            a  = [
                str(uc.ufloat(self.popt[0],perr[0]))
            ]*2
            m  = [
                str(uc.ufloat(                         self.popt[1] ,                            perr[1] )), 
                str(uc.ufloat(calibration.applyToValue(self.popt[1]),calibration.applyToDistance(perr[1])))
            ]
            si = [
                str(uc.ufloat(                            self.popt[2] ,                            perr[2] )),
                str(uc.ufloat(calibration.applyToDistance(self.popt[2]),calibration.applyToDistance(perr[2])))
            ]
            dict_params.update({"Amplitude":a,"Mean":m,"Sigma":si})
        elif self.fit_type == 2:
            # Gaussian + const.
            a  = [
                str(uc.ufloat(self.popt[0],perr[0]))
            ]*2
            m  = [
                str(uc.ufloat(                         self.popt[1] ,                            perr[1] )), 
                str(uc.ufloat(calibration.applyToValue(self.popt[1]),calibration.applyToDistance(perr[1])))
            ]
            si = [
                str(uc.ufloat(                            self.popt[2] ,                            perr[2] )),
                str(uc.ufloat(calibration.applyToDistance(self.popt[2]),calibration.applyToDistance(perr[2])))
            ]
            c = [
                str(uc.ufloat(self.popt[3],perr[3]))
            ]*2
            dict_params.update({"Amplitude":a,"Mean":m,"Sigma":si,"Constant":c})
        elif self.fit_type == 3:
            # Gaussian + lin.
            a  = [
                str(uc.ufloat(self.popt[0],perr[0]))
            ]*2
            m  = [
                str(uc.ufloat(                         self.popt[1] ,                            perr[1] )), 
                str(uc.ufloat(calibration.applyToValue(self.popt[1]),calibration.applyToDistance(perr[1])))
            ]
            si = [
                str(uc.ufloat(                            self.popt[2] ,                            perr[2] )),
                str(uc.ufloat(calibration.applyToDistance(self.popt[2]),calibration.applyToDistance(perr[2])))
            ]
            c = [
                str(uc.ufloat(self.popt[3],perr[3]))
            ]*2
            sl  = [
                str(uc.ufloat(                                self.popt[4],                                 perr[4] )),
                str(uc.ufloat(1/calibration.applyToDistance(1/self.popt[4]),1/calibration.applyToDistance(1/perr[4])))
            ]
            dict_params.update({"Amplitude":a,"Mean":m,"Sigma":si,"Constant":c,"Slope":sl})
        else:
            print("Invalid Fitting State in FitInfo.get_parameters:",self.fit_type)
            return

        if self.fit_type < 4 and self.fit_type > 0:
            dict_params.update({
                    "χ²":     (str(round(self.chisq,2))    , ""), 
                    "red. χ²":(str(round(self.red_chisq,2)), ""), 
                    "DoF":    (str(self.dof)               , "")
                })

        return dict_params
    
    def plot(self):
        X = self.record_info.fitplot_x(10)

        if self.popt is None:
            return [], []
        Y = self._f(X, *self.popt)

        # Create mask of unnecessary curve information
        rounded = np.around(Y,1)
        similar = rounded[1:] == rounded[:-1]
        edges = similar[1:]^similar[:-1]
        mask = np.append(
                np.append(True, np.logical_or(~similar[1:],edges)),
                True)
        return X[mask], Y[mask]

## Levenberg-Marquardt Fits

def curve_fit_general_gauss(centers, events, cutoff, f, p0_ext = []):
    # Init Values
    centers = centers[events>=cutoff]
    events = events[events>=cutoff]
    uncertainties = np.maximum(np.sqrt(events),np.sqrt(10))
    
    if len(events) == 0:
        return None, {"No Events":"above Threshold"}, None, None, None
    
    # Guesses
    height = np.max(events)
    mean = np.average(centers, weights=events)
    sigma = np.sqrt(np.sum(events*(centers-mean)**2)/(np.sum(events)-1))

    p0 = [height, mean, sigma]
    p0.extend(p0_ext)

    if len(events) < len(p0):
        return None, {"Not enough Bins":"above Threshold"}, None, None, None
    elif np.sum(events) == 0:
        popt = np.zeros(len(p0))
        pcov = np.zeros(len(p0))
        return popt, pcov, 0, 0

    popt = None
    pcov = None

    with warnings.catch_warnings():
        warnings.simplefilter("error", OptimizeWarning)
        try:
            #string = str(f)+", "+str(centers)+","+str(events)+","+str(p0)+ ","+str( uncertainties)+","+str(threading.current_thread())
            #print(string)
            #print(type(f), ", ", type(centers), "," , type(events), ",", type(p0), ",", type(uncertainties))
            popt, pcov = curve_fit(f, centers, events, p0, sigma = uncertainties)
        except OptimizeWarning:
            return None, {"(O) No":"Convergence"}, None, None, None
        except RuntimeError:
            return None, {"(R) No":"Convergence"}, None, None, None
    
    r = events - f(centers, *popt)
    chisq = np.sum((r / uncertainties) ** 2)
    dof = len(events)-len(p0)
    #print("len events",len(events),"len p0",len(p0))
    red_chisq = chisq/dof
    #print("POPT",popt, "PCOV", pcov, "CHISQ", chisq, "RED_CHISQ", red_chisq, "DOF", dof)
    return popt, pcov, chisq, red_chisq, dof

## Gauss Functions

def gauss_lin(x, height, mean, sigma, const, lin):
    return height/(sigma*np.sqrt(2*np.pi))*np.exp(-(x-mean)**2/(2*sigma**2)) + lin*x+const

def gauss_const(x, height, mean, sigma, const):
    return gauss_lin(x, height, mean, sigma, const, 0)

def gauss(x, height, mean, sigma):
    return gauss_lin(x, height, mean, sigma, 0, 0)

## Matrix Inversion Fits

def fast_fit_single_gauss(centers, events, cutoff = 10):
    # If every event count is equal, this throws an error!
    # Fit
    centers = centers[events>=cutoff]
    events = events[events>=cutoff]
    log_events = np.log(events)
    result_lin = fast_fit_parabola(centers,log_events)
    sigma = np.sqrt(-1/(2*result_lin[2]))
    mu = result_lin[1]*sigma**2
    a = np.exp(result_lin[0]-mu**2*result_lin[2])
    
    # Chi Squared
    left = centers - 0.5
    right = centers + 0.5
    sqrt2 = np.sqrt(2)
    estimated = np.sqrt(np.pi/2)*a*sigma*(erf((mu-left)/(sqrt2*sigma))-erf((mu-right)/(sqrt2*sigma)))
    chi_squared = np.sum((events-estimated)**2/estimated)
    reduced_chi_squared = chi_squared/(len(events)-3)
    return [a,mu,sigma], chi_squared, reduced_chi_squared
    
def fast_fit_parabola(centers, events):
    sum1 = np.sum(centers)
    sum2 = np.sum(centers**2)
    sum3 = np.sum(centers**3)
    sum4 = np.sum(centers**4)
    matrix = np.array([[len(centers),sum1,sum2],
                       [sum1, sum2, sum3],
                       [sum2, sum3, sum4]])
    inv_matrix = np.linalg.inv(matrix)
    b = np.array([np.sum(events),np.sum(events*centers),np.sum(events*centers**2)])
    return inv_matrix.dot(b)

def fast_fit_lin(centers, events):
    sum1 = np.sum(centers)
    sum2 = np.sum(centers**2)
    matrix = np.array([[len(centers),sum1],
                       [sum1, sum2]])
    inv_matrix = np.linalg.inv(matrix)
    b = np.array([np.sum(events),np.sum(events*centers)])
    return inv_matrix.dot(b)
