;;Instance with 1x8x1 points
(define (problem dragonfly-p03) (:domain dragonfly)
(:objects
pad_0_0_0 - lilypad
pad_0_1_0 - lilypad
pad_0_2_0 - lilypad
pad_0_3_0 - lilypad
pad_0_4_0 - lilypad
pad_0_5_0 - lilypad
pad_0_6_0 - lilypad
pad_0_7_0 - lilypad
)
(:init (= (north) 0) (= (east) 0) (= (up) 0)
 (= (min_north) 0)  (= (max_north) 1)
 (= (min_east) 0)  (= (max_east) 8)
 (= (min_up) 0)  (= (max_up) 1)
(= (pad_north pad_0_0_0) 0)
(= (pad_east pad_0_0_0) 0)
(= (pad_up pad_0_0_0) 0)
(= (pad_north pad_0_1_0) 0)
(= (pad_east pad_0_1_0) 1)
(= (pad_up pad_0_1_0) 0)
(= (pad_north pad_0_2_0) 0)
(= (pad_east pad_0_2_0) 2)
(= (pad_up pad_0_2_0) 0)
(= (pad_north pad_0_3_0) 0)
(= (pad_east pad_0_3_0) 3)
(= (pad_up pad_0_3_0) 0)
(= (pad_north pad_0_4_0) 0)
(= (pad_east pad_0_4_0) 4)
(= (pad_up pad_0_4_0) 0)
(= (pad_north pad_0_5_0) 0)
(= (pad_east pad_0_5_0) 5)
(= (pad_up pad_0_5_0) 0)
(= (pad_north pad_0_6_0) 0)
(= (pad_east pad_0_6_0) 6)
(= (pad_up pad_0_6_0) 0)
(= (pad_north pad_0_7_0) 0)
(= (pad_east pad_0_7_0) 7)
(= (pad_up pad_0_7_0) 0)
(= (nectar-level) 21)
(= (nectar-level-full) 21)
)
(:goal (and
(alighted pad_0_0_0)
(alighted pad_0_1_0)
(alighted pad_0_2_0)
(alighted pad_0_3_0)
(alighted pad_0_4_0)
(alighted pad_0_5_0)
(alighted pad_0_6_0)
(alighted pad_0_7_0)
(= (north) 0) (= (east) 0) (= (up) 0) ))
);; end of the problem instance
