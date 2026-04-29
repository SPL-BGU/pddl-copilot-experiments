(define (problem farmland_6_pairs)
  (:domain farmland)
  (:objects
    farm0 farm1 farm2 farm3 farm4 farm5 - farm
  )
  (:init
    (= (cost) 0)
    (= (x farm0) 6)
    (= (x farm1) 0)
    (= (x farm2) 6)
    (= (x farm3) 0)
    (= (x farm4) 6)
    (= (x farm5) 0)
    (adj farm0 farm1)
    (adj farm1 farm0)
    (adj farm2 farm3)
    (adj farm3 farm2)
    (adj farm4 farm5)
    (adj farm5 farm4)
  )
  (:goal
    (and
      (>= (x farm1) 1)
      (>= (x farm3) 1)
      (>= (x farm5) 1)
    )
  )
)
