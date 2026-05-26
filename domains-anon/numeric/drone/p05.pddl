;;Instance with 2x9x1 points
(define (problem name) (:domain dragonfly)
(:objects
pad_0_0_0 - lilypad
pad_0_1_0 - lilypad
pad_0_2_0 - lilypad
pad_0_3_0 - lilypad
pad_0_4_0 - lilypad
pad_0_5_0 - lilypad
pad_0_6_0 - lilypad
pad_0_7_0 - lilypad
pad_0_8_0 - lilypad
pad_1_0_0 - lilypad
pad_1_1_0 - lilypad
pad_1_2_0 - lilypad
pad_1_3_0 - lilypad
pad_1_4_0 - lilypad
pad_1_5_0 - lilypad
pad_1_6_0 - lilypad
pad_1_7_0 - lilypad
pad_1_8_0 - lilypad
)
(:init (= (north) 0) (= (east) 0) (= (up) 0)
 (= (min_north) 0)  (= (max_north) 2)
 (= (min_east) 0)  (= (max_east) 9)
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
(= (pad_north pad_0_8_0) 0)
(= (pad_east pad_0_8_0) 8)
(= (pad_up pad_0_8_0) 0)
(= (pad_north pad_1_0_0) 1)
(= (pad_east pad_1_0_0) 0)
(= (pad_up pad_1_0_0) 0)
(= (pad_north pad_1_1_0) 1)
(= (pad_east pad_1_1_0) 1)
(= (pad_up pad_1_1_0) 0)
(= (pad_north pad_1_2_0) 1)
(= (pad_east pad_1_2_0) 2)
(= (pad_up pad_1_2_0) 0)
(= (pad_north pad_1_3_0) 1)
(= (pad_east pad_1_3_0) 3)
(= (pad_up pad_1_3_0) 0)
(= (pad_north pad_1_4_0) 1)
(= (pad_east pad_1_4_0) 4)
(= (pad_up pad_1_4_0) 0)
(= (pad_north pad_1_5_0) 1)
(= (pad_east pad_1_5_0) 5)
(= (pad_up pad_1_5_0) 0)
(= (pad_north pad_1_6_0) 1)
(= (pad_east pad_1_6_0) 6)
(= (pad_up pad_1_6_0) 0)
(= (pad_north pad_1_7_0) 1)
(= (pad_east pad_1_7_0) 7)
(= (pad_up pad_1_7_0) 0)
(= (pad_north pad_1_8_0) 1)
(= (pad_east pad_1_8_0) 8)
(= (pad_up pad_1_8_0) 0)
(= (nectar-level) 25)
(= (nectar-level-full) 25)
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
(alighted pad_0_8_0)
(alighted pad_1_0_0)
(alighted pad_1_1_0)
(alighted pad_1_2_0)
(alighted pad_1_3_0)
(alighted pad_1_4_0)
(alighted pad_1_5_0)
(alighted pad_1_6_0)
(alighted pad_1_7_0)
(alighted pad_1_8_0)
(= (north) 0) (= (east) 0) (= (up) 0) ))
);; end of the problem instance
