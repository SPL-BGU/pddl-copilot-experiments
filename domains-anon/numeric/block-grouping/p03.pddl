;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_20_5_2_1)
  (:domain mt-bonbon-tray)
  (:objects
    bonbon1 bonbon2 bonbon3 bonbon4 bonbon5 - bonbon
  )

  (:init
    (= (lane bonbon3) 17)
  (= (tier bonbon3) 14)
  (= (lane bonbon4) 17)
  (= (tier bonbon4) 8)
  (= (lane bonbon2) 19)
  (= (tier bonbon2) 5)
  (= (lane bonbon1) 20)
  (= (tier bonbon1) 14)
  (= (lane bonbon5) 5)
  (= (tier bonbon5) 5)
  (= (max_lane) 20 )
  (= (min_lane) 1 )
  (= (max_tier) 20 )
  (= (min_tier) 1 )
  )

  (:goal (and
    (= (lane bonbon1) (lane bonbon2))
(= (tier bonbon1) (tier bonbon2))
  (= (lane bonbon1) (lane bonbon3))
(= (tier bonbon1) (tier bonbon3))
  (= (lane bonbon1) (lane bonbon4))
(= (tier bonbon1) (tier bonbon4))
  (or (not (= (lane bonbon1) (lane bonbon5))) (not (= (tier bonbon1) (tier bonbon5))))
  (= (lane bonbon2) (lane bonbon3))
(= (tier bonbon2) (tier bonbon3))
  (= (lane bonbon2) (lane bonbon4))
(= (tier bonbon2) (tier bonbon4))
  (or (not (= (lane bonbon2) (lane bonbon5))) (not (= (tier bonbon2) (tier bonbon5))))
  (= (lane bonbon3) (lane bonbon4))
(= (tier bonbon3) (tier bonbon4))
  (or (not (= (lane bonbon3) (lane bonbon5))) (not (= (tier bonbon3) (tier bonbon5))))
  (or (not (= (lane bonbon4) (lane bonbon5))) (not (= (tier bonbon4) (tier bonbon5))))
  ))





)
