(define (problem farmland_6_pairs)
  (:domain orbital)
  (:objects
    module0 module1 module2 module3 module4 module5 - module
  )
  (:init
    (= (power_drain) 0)
    (= (oxygen module0) 6)
    (= (oxygen module1) 0)
    (= (oxygen module2) 6)
    (= (oxygen module3) 0)
    (= (oxygen module4) 6)
    (= (oxygen module5) 0)
    (linked module0 module1)
    (linked module1 module0)
    (linked module2 module3)
    (linked module3 module2)
    (linked module4 module5)
    (linked module5 module4)
  )
  (:goal
    (and
      (>= (oxygen module1) 1)
      (>= (oxygen module3) 1)
      (>= (oxygen module5) 1)
    )
  )
)
