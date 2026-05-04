(define   (problem parking)
  (:domain parking)
  (:objects
     car_0  car_1  car_2 - car
     curb_0 curb_1 curb_2 - curb
  )

  (:goal
    (and
      (at-curb-num car_0 curb_0)
      (at-curb-num car_1 curb_1)
      (at-curb-num car_2 curb_2)
    )
  )
(:metric minimize (total-cost))
)
; =========== INIT ===========
;  curb_0: car_2 car_1
;  curb_1: car_0
;  curb_2:
; ========== /INIT ===========

; =========== GOAL ===========
;  curb_0: car_0
;  curb_1: car_1
;  curb_2: car_2
; =========== /GOAL ===========
