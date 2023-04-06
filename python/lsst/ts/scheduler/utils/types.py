from lsst.ts.salobj import DefaultingValidator

__all__ = [
    "ValidationRules",
]

"""This type alias represents a dictionary where the keys are tuples containing
a string and a boolean value, and the values are instances of
`DefaultingValidator` class."""
ValidationRules = dict[(str, bool), DefaultingValidator]
