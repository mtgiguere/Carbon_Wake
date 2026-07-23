"""The reactivity science core — pure, deterministic, I/O-free.

This subpackage answers exactly one question: *given a mass of seafloor organic
carbon disturbed by trawling, and a named published assumption about how much of
it remineralizes to CO2, what is the resulting CO2 estimate?*

The whole point of the project lives here: the "named published assumption" is
disputed by one to two orders of magnitude in the literature, so this core is
built to hold several competing presets side by side and to expose the *range*,
never a single false-precision number.

Nothing in this subpackage may import a web framework, a database driver, or a
geospatial library. If you feel the urge, the logic belongs in a different layer.
"""
