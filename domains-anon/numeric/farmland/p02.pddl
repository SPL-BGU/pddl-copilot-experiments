(define (problem orbital-p02)
  (:domain orbital)
  (:objects
    module0 module1 module2 module3 - module
  )
  (:init
    (= (power_drain) 0)
    (= (oxygen module0) 8)
    (= (oxygen module1) 0)
    (= (oxygen module2) 0)
    (= (oxygen module3) 0)
    (linked module0 module1)
    (linked module1 module0)
    (linked module1 module2)
    (linked module2 module1)
    (linked module2 module3)
    (linked module3 module2)
  )
  (:goal
    (and
      (>= (oxygen module1) 1)
      (>= (oxygen module2) 1)
      (>= (oxygen module3) 1)
    )
  )
)
