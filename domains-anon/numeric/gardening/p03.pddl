;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem assembly-line-constrained-p03)
  (:domain assembly-line-constrained)
  (:objects
    robot_arm1 - robot_arm
  stock_bin1 - stock_bin
  workstation1 - workstation
  )

  (:init
    (= (ceiling) 20)
  (= (east_edge) 7)
  (= (west_edge) 1)
  (= (north_edge) 7)
  (= (south_edge) 1)
  (= (held_stock) 0)
  (= (total_delivered) 0)
  (= (total_drawn) 0)
  (= (delivered_to workstation1) 0)
  (= (col robot_arm1) 7)
  (= (row robot_arm1) 6)
  (= (col workstation1) 1)
  (= (row workstation1) 1)
  (= (col stock_bin1) 6)
  (= (row stock_bin1) 6)
  )

  (:goal (and
    (= (delivered_to workstation1) 9)
  (= (total_delivered) (delivered_to workstation1) )
  ))





)
