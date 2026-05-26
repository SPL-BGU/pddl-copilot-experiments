;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_25_5_2_2)
  (:domain mt-bonbon-tray)
  (:objects
    bonbon1 bonbon2 bonbon3 bonbon4 bonbon5 - bonbon
  )

  (:init
    (= (lane bonbon3) 11)
  (= (tier bonbon3) 16)
  (= (lane bonbon4) 23)
  (= (tier bonbon4) 22)
  (= (lane bonbon2) 13)
  (= (tier bonbon2) 18)
  (= (lane bonbon1) 9)
  (= (tier bonbon1) 12)
  (= (lane bonbon5) 8)
  (= (tier bonbon5) 6)
  (= (max_lane) 25 )
  (= (min_lane) 1 )
  (= (max_tier) 25 )
  (= (min_tier) 1 )
  )

  (:goal (and
    (= (lane bonbon1) (lane bonbon2))
(= (tier bonbon1) (tier bonbon2))
  (= (lane bonbon1) (lane bonbon3))
(= (tier bonbon1) (tier bonbon3))
  (or (not (= (lane bonbon1) (lane bonbon4))) (not (= (tier bonbon1) (tier bonbon4))))
  (= (lane bonbon1) (lane bonbon5))
(= (tier bonbon1) (tier bonbon5))
  (= (lane bonbon2) (lane bonbon3))
(= (tier bonbon2) (tier bonbon3))
  (or (not (= (lane bonbon2) (lane bonbon4))) (not (= (tier bonbon2) (tier bonbon4))))
  (= (lane bonbon2) (lane bonbon5))
(= (tier bonbon2) (tier bonbon5))
  (or (not (= (lane bonbon3) (lane bonbon4))) (not (= (tier bonbon3) (tier bonbon4))))
  (= (lane bonbon3) (lane bonbon5))
(= (tier bonbon3) (tier bonbon5))
  (or (not (= (lane bonbon4) (lane bonbon5))) (not (= (tier bonbon4) (tier bonbon5))))
  ))





)
