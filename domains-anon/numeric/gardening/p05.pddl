;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_8_1_2)
  (:domain assembly-line-constrained)
  (:objects
    robot_arm1 - robot_arm
  stock_bin1 - stock_bin
  workstation1 - workstation
  )

  (:init
    (= (ceiling) 20)
  (= (east_edge) 8)
  (= (west_edge) 1)
  (= (north_edge) 8)
  (= (south_edge) 1)
  (= (held_stock) 0)
  (= (total_delivered) 0)
  (= (total_drawn) 0)
  (= (delivered_to workstation1) 0)
  (= (col robot_arm1) 6)
  (= (row robot_arm1) 6)
  (= (col workstation1) 5)
  (= (row workstation1) 5)
  (= (col stock_bin1) 4)
  (= (row stock_bin1) 4)
  )

  (:goal (and
    (= (delivered_to workstation1) 1)
  (= (total_delivered) (delivered_to workstation1) )
  ))





)
