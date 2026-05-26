;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_15_5_2_1)
  (:domain mt-bonbon-tray)
  (:objects
    bonbon1 bonbon2 bonbon3 bonbon4 bonbon5 - bonbon
  )

  (:init
    (= (lane bonbon3) 1)
  (= (tier bonbon3) 2)
  (= (lane bonbon4) 10)
  (= (tier bonbon4) 10)
  (= (lane bonbon2) 13)
  (= (tier bonbon2) 3)
  (= (lane bonbon1) 13)
  (= (tier bonbon1) 10)
  (= (lane bonbon5) 13)
  (= (tier bonbon5) 10)
  (= (max_lane) 15 )
  (= (min_lane) 1 )
  (= (max_tier) 15 )
  (= (min_tier) 1 )
  )

  (:goal (and
    (= (lane bonbon1) (lane bonbon2))
(= (tier bonbon1) (tier bonbon2))
  (or (not (= (lane bonbon1) (lane bonbon3))) (not (= (tier bonbon1) (tier bonbon3))))
  (= (lane bonbon1) (lane bonbon4))
(= (tier bonbon1) (tier bonbon4))
  (= (lane bonbon1) (lane bonbon5))
(= (tier bonbon1) (tier bonbon5))
  (or (not (= (lane bonbon2) (lane bonbon3))) (not (= (tier bonbon2) (tier bonbon3))))
  (= (lane bonbon2) (lane bonbon4))
(= (tier bonbon2) (tier bonbon4))
  (= (lane bonbon2) (lane bonbon5))
(= (tier bonbon2) (tier bonbon5))
  (or (not (= (lane bonbon3) (lane bonbon4))) (not (= (tier bonbon3) (tier bonbon4))))
  (or (not (= (lane bonbon3) (lane bonbon5))) (not (= (tier bonbon3) (tier bonbon5))))
  (= (lane bonbon4) (lane bonbon5))
(= (tier bonbon4) (tier bonbon5))
  ))





)
