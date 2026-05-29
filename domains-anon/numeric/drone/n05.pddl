;;Instance with 1x1x2 points
(define (problem dragonfly-n05)
  (:domain dragonfly)
  (:objects
    pad_0_0_0 - lilypad
    pad_0_0_1 - lilypad
  )

  (:goal
    (and
      (alighted pad_0_0_0)
      (alighted pad_0_0_1)
      (= (north) 0) (= (east) 0) (= (up) 0))
  )
);; end of the problem instance
