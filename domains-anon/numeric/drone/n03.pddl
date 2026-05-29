;;Instance with 1x1x2 points
(define (problem dragonfly-n03)
  (:domain dragonfly)
  (:objects
    pad_0_0_0 - lilypad
    pad_0_0_1 - lilypad
  )
  (:init
    (= (north) 0)
    (= (east) 0)
    (= (up) 0)
    (= (min_north) 0)
    (= (max_north) 1)
    (= (min_east) 0)
    (= (max_east) 1)
    (= (min_up) 0)
    (= (max_up) 2)
    (= (pad_north pad_0_0_0) 0)
    (= (pad_east pad_0_0_0) 0)
    (= (pad_up pad_0_0_0) 0)
    (= (pad_north pad_0_0_1) 0)
    (= (pad_east pad_0_0_1) 0)
    (= (pad_up pad_0_0_1) 1)
    (= (nectar-level) 9)
    (= (nectar-level-full) 9)
  )
  (:goal
    (and
      (undef_pred_xyz pad_0_0_0)
      (alighted pad_0_0_1)
      (= (north) 0) (= (east) 0) (= (up) 0))
  )
);; end of the problem instance
