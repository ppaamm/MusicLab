from instruments.additive import make_spectral_frequency, PartialCharacteristics
from instruments.envelopes.adsr import ADSR


# Using the work of https://ccrma.stanford.edu/~sdill/220A-project/drums.html#add


def make_steel_drum(master, velocity_curve):
    partials = {
        1.00: PartialCharacteristics(1.0, 0.0, ADSR(0.05, 0.02, 0.01, 0.01)), 
        2.00: PartialCharacteristics(0.2, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        2.60: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        3.20: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        5.60: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        8.20: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        2.90: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        3.00: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        4.20: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)), 
        6.60: PartialCharacteristics(0.1, 0.0, ADSR(0.01, 0.02, 0.01, 0.01)),
    }

    return make_spectral_frequency(partials=partials, master=master, velocity_curve=velocity_curve)



def make_clock_bell(master, velocity_curve):
    partials = {
        1.00: PartialCharacteristics(0.5, 0.0, ADSR(0.005, 0.05, 0.5, 0.4)),
        1.30: PartialCharacteristics(0.1, 0.0, ADSR(0.005, 0.04, 0.3, 0.3)),
        1.60: PartialCharacteristics(0.1, 0.0, ADSR(0.005, 0.04, 0.3, 0.3)),
        1.90: PartialCharacteristics(0.1, 0.0, ADSR(0.005, 0.03, 0.2, 0.25)),
        2.20: PartialCharacteristics(0.1, 0.0, ADSR(0.005, 0.03, 0.2, 0.25))
    }
    
    return make_spectral_frequency(partials=partials, master=master, velocity_curve=velocity_curve)



def make_high_metallic_chime(master, velocity_curve):
    partials = {
        1.00: PartialCharacteristics(0.30, 0.0, ADSR(0.005, 0.05, 0.6, 0.3)),
        3.00: PartialCharacteristics(0.20, 0.0, ADSR(0.005, 0.04, 0.4, 0.3)),
        5.00: PartialCharacteristics(0.10, 0.0, ADSR(0.005, 0.03, 0.3, 0.25)),
        7.00: PartialCharacteristics(0.10, 0.0, ADSR(0.005, 0.03, 0.2, 0.20)),
        9.00: PartialCharacteristics(0.10, 0.0, ADSR(0.005, 0.03, 0.2, 0.20))
    }
    
    return make_spectral_frequency(partials=partials, master=master, velocity_curve=velocity_curve)


def make_small_gong(master, velocity_curve):
    partials = {
        0.04: PartialCharacteristics(0.079, 0.0, ADSR(0.001, 0.035, 0.000, 0.030)),
        3.00: PartialCharacteristics(0.792, 0.0, ADSR(0.001, 0.030, 0.000, 0.025)),
        4.08: PartialCharacteristics(0.127, 0.0, ADSR(0.001, 0.030, 0.000, 0.025)),
        6.02: PartialCharacteristics(0.253, 0.0, ADSR(0.001, 0.030, 0.000, 0.025)),
        7.08: PartialCharacteristics(0.177, 0.0, ADSR(0.001, 0.030, 0.000, 0.025)),
        7.88: PartialCharacteristics(0.773, 0.0, ADSR(0.001, 0.030, 0.000, 0.025)),
        8.57: PartialCharacteristics(0.053, 0.0, ADSR(0.001, 0.030, 0.000, 0.025)),
        10.90: PartialCharacteristics(0.119, 0.0, ADSR(0.001, 0.030, 0.000, 0.025)),
        11.89: PartialCharacteristics(0.176, 0.0, ADSR(0.001, 0.022, 0.000, 0.018)),
        12.64: PartialCharacteristics(0.078, 0.0, ADSR(0.001, 0.022, 0.000, 0.018)),
        13.22: PartialCharacteristics(0.067, 0.0, ADSR(0.001, 0.022, 0.000, 0.018)),
        13.81: PartialCharacteristics(0.075, 0.0, ADSR(0.001, 0.022, 0.000, 0.018)),
        14.91: PartialCharacteristics(1.000, 0.0, ADSR(0.001, 0.022, 0.000, 0.018)),
        20.97: PartialCharacteristics(0.092, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        22.13: PartialCharacteristics(0.065, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        22.96: PartialCharacteristics(0.096, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        23.81: PartialCharacteristics(0.048, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        28.04: PartialCharacteristics(0.053, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        28.99: PartialCharacteristics(0.011, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        31.60: PartialCharacteristics(0.075, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        32.06: PartialCharacteristics(0.049, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        35.00: PartialCharacteristics(0.073, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        38.82: PartialCharacteristics(0.053, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        39.49: PartialCharacteristics(0.066, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        42.12: PartialCharacteristics(0.050, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        47.03: PartialCharacteristics(0.050, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        50.88: PartialCharacteristics(0.045, 0.0, ADSR(0.001, 0.018, 0.000, 0.014)),
        51.62: PartialCharacteristics(0.051, 0.0, ADSR(0.001, 0.018, 0.000, 0.014))
    }
    
    return make_spectral_frequency(partials=partials, master=master, velocity_curve=velocity_curve)


