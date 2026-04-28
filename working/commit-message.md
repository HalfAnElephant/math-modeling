feat(c-uav-inspection): implement reproducible multi-UAV inspection model

Build complete Problem C experiment workflow with divisible hover time
allocation, normalized multi-objective scoring, and closed-loop ground
review with rebuild search. All constraints verified: hover time splits
across UAVs/sorties, threshold uses max(base, direct*multiplier), and
ground personnel depart after all UAV tasks complete.
