;;Instance with 1x1x4 points
(define (problem dragonfly-p02) (:domain dragonfly)
(:objects
pad_0_0_0 - lilypad
pad_0_0_1 - lilypad
pad_0_0_2 - lilypad
pad_0_0_3 - lilypad
)
(:init (= (north) 0) (= (east) 0) (= (up) 0)
 (= (min_north) 0)  (= (max_north) 1)
 (= (min_east) 0)  (= (max_east) 1)
 (= (min_up) 0)  (= (max_up) 4)
(= (pad_north pad_0_0_0) 0)
(= (pad_east pad_0_0_0) 0)
(= (pad_up pad_0_0_0) 0)
(= (pad_north pad_0_0_1) 0)
(= (pad_east pad_0_0_1) 0)
(= (pad_up pad_0_0_1) 1)
(= (pad_north pad_0_0_2) 0)
(= (pad_east pad_0_0_2) 0)
(= (pad_up pad_0_0_2) 2)
(= (pad_north pad_0_0_3) 0)
(= (pad_east pad_0_0_3) 0)
(= (pad_up pad_0_0_3) 3)
(= (nectar-level) 13)
(= (nectar-level-full) 13)
)
(:goal (and
(alighted pad_0_0_0)
(alighted pad_0_0_1)
(alighted pad_0_0_2)
(alighted pad_0_0_3)
(= (north) 0) (= (east) 0) (= (up) 0) ))
);; end of the problem instance
