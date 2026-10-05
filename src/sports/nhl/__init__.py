"""The NHL (Stages 51 and 55 to 58): the data probe, then the pipeline.

`schedule.py` reads the league's schedule and results into the core's
schedule shape (Stage 55). The module object the core reads, `SPORT`,
arrives once the lock rule and the model exist.
"""
