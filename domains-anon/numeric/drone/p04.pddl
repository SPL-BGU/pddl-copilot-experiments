;;Instance with 8x1x2 points
(define (problem name) (:domain dragonfly)
(:objects
pad_0_0_0 - lilypad
pad_0_0_1 - lilypad
pad_1_0_0 - lilypad
pad_1_0_1 - lilypad
pad_2_0_0 - lilypad
pad_2_0_1 - lilypad
pad_3_0_0 - lilypad
pad_3_0_1 - lilypad
pad_4_0_0 - lilypad
pad_4_0_1 - lilypad
pad_5_0_0 - lilypad
pad_5_0_1 - lilypad
pad_6_0_0 - lilypad
pad_6_0_1 - lilypad
pad_7_0_0 - lilypad
pad_7_0_1 - lilypad
)
(:init (= (north) 0) (= (east) 0) (= (up) 0)
 (= (min_north) 0)  (= (max_north) 8)
 (= (min_east) 0)  (= (max_east) 1)
 (= (min_up) 0)  (= (max_up) 2)
(= (pad_north pad_0_0_0) 0)
(= (pad_east pad_0_0_0) 0)
(= (pad_up pad_0_0_0) 0)
(= (pad_north pad_0_0_1) 0)
(= (pad_east pad_0_0_1) 0)
(= (pad_up pad_0_0_1) 1)
(= (pad_north pad_1_0_0) 1)
(= (pad_east pad_1_0_0) 0)
(= (pad_up pad_1_0_0) 0)
(= (pad_north pad_1_0_1) 1)
(= (pad_east pad_1_0_1) 0)
(= (pad_up pad_1_0_1) 1)
(= (pad_north pad_2_0_0) 2)
(= (pad_east pad_2_0_0) 0)
(= (pad_up pad_2_0_0) 0)
(= (pad_north pad_2_0_1) 2)
(= (pad_east pad_2_0_1) 0)
(= (pad_up pad_2_0_1) 1)
(= (pad_north pad_3_0_0) 3)
(= (pad_east pad_3_0_0) 0)
(= (pad_up pad_3_0_0) 0)
(= (pad_north pad_3_0_1) 3)
(= (pad_east pad_3_0_1) 0)
(= (pad_up pad_3_0_1) 1)
(= (pad_north pad_4_0_0) 4)
(= (pad_east pad_4_0_0) 0)
(= (pad_up pad_4_0_0) 0)
(= (pad_north pad_4_0_1) 4)
(= (pad_east pad_4_0_1) 0)
(= (pad_up pad_4_0_1) 1)
(= (pad_north pad_5_0_0) 5)
(= (pad_east pad_5_0_0) 0)
(= (pad_up pad_5_0_0) 0)
(= (pad_north pad_5_0_1) 5)
(= (pad_east pad_5_0_1) 0)
(= (pad_up pad_5_0_1) 1)
(= (pad_north pad_6_0_0) 6)
(= (pad_east pad_6_0_0) 0)
(= (pad_up pad_6_0_0) 0)
(= (pad_north pad_6_0_1) 6)
(= (pad_east pad_6_0_1) 0)
(= (pad_up pad_6_0_1) 1)
(= (pad_north pad_7_0_0) 7)
(= (pad_east pad_7_0_0) 0)
(= (pad_up pad_7_0_0) 0)
(= (pad_north pad_7_0_1) 7)
(= (pad_east pad_7_0_1) 0)
(= (pad_up pad_7_0_1) 1)
(= (nectar-level) 23)
(= (nectar-level-full) 23)
)
(:goal (and
(alighted pad_0_0_0)
(alighted pad_0_0_1)
(alighted pad_1_0_0)
(alighted pad_1_0_1)
(alighted pad_2_0_0)
(alighted pad_2_0_1)
(alighted pad_3_0_0)
(alighted pad_3_0_1)
(alighted pad_4_0_0)
(alighted pad_4_0_1)
(alighted pad_5_0_0)
(alighted pad_5_0_1)
(alighted pad_6_0_0)
(alighted pad_6_0_1)
(alighted pad_7_0_0)
(alighted pad_7_0_1)
(= (north) 0) (= (east) 0) (= (up) 0) ))
);; end of the problem instance
