;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem assembly-line-constrained-n02)
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
  (= (col robot_arm1) 1)
  (= (row robot_arm1) 5)
  (= (col workstation1) 2)
  (= (row workstation1) 2)
  (= (col stock_bin1) 2)
  (= (row stock_bin1) 2)

    (ceiling undef_obj_xyz))

  (:goal (and
    (= (delivered_to workstation1) 1)
  (= (total_delivered) (delivered_to workstation1) )
  ))





)
