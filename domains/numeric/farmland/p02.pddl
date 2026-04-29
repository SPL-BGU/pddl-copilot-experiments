(define (problem farmland_4_chain)
  (:domain farmland)
  (:objects
    farm0 farm1 farm2 farm3 - farm
  )
  (:init
    (= (cost) 0)
    (= (x farm0) 8)
    (= (x farm1) 0)
    (= (x farm2) 0)
    (= (x farm3) 0)
    (adj farm0 farm1)
    (adj farm1 farm0)
    (adj farm1 farm2)
    (adj farm2 farm1)
    (adj farm2 farm3)
    (adj farm3 farm2)
  )
  (:goal
    (and
      (>= (x farm1) 1)
      (>= (x farm2) 1)
      (>= (x farm3) 1)
    )
  )
)
