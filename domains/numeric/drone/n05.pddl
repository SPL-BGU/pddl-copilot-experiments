;;Instance with 1x1x2 points
(define (problem name)
  (:domain drone)
  (:objects
    x0y0z0 - location
    x0y0z1 - location
  )
  
  (:goal
    (and
      (visited x0y0z0)
      (visited x0y0z1)
      (= (x) 0) (= (y) 0) (= (z) 0))
  )
);; end of the problem instance