from instruments.additive import make_spectral_frequency, PartialCharacteristics
from instruments.envelopes.adsr import ADSR


def make_piano(master, velocity_curve):
    partials = {
        1.00: PartialCharacteristics(1.0, 0.0, ADSR(0.002, 0.05, 0.6, 0.6)),
        2.01: PartialCharacteristics(0.6, 0.0, ADSR(0.002, 0.04, 0.4, 0.5)),
        3.03: PartialCharacteristics(0.4, 0.0, ADSR(0.002, 0.03, 0.3, 0.4)),
        4.06: PartialCharacteristics(0.3, 0.0, ADSR(0.002, 0.03, 0.2, 0.4)),
        5.10: PartialCharacteristics(0.2, 0.0, ADSR(0.002, 0.03, 0.2, 0.4)),
        6.15: PartialCharacteristics(0.15, 0.0, ADSR(0.002, 0.03, 0.1, 0.4)),
        7.20: PartialCharacteristics(0.10, 0.0, ADSR(0.002, 0.03, 0.1, 0.4)),
        8.27: PartialCharacteristics(0.08, 0.0, ADSR(0.002, 0.03, 0.1, 0.4)),
        9.35: PartialCharacteristics(0.06, 0.0, ADSR(0.002, 0.03, 0.1, 0.4)),
        10.45: PartialCharacteristics(0.05, 0.0, ADSR(0.002, 0.03, 0.1, 0.4))
    }

    return make_spectral_frequency(partials=partials, master=master, velocity_curve=velocity_curve)