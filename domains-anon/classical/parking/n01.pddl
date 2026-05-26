(define   (problem parking)
  (:domain apiary)
  (:objects
     bee_0  bee_1  bee_2 - bee
     flower_0 flower_1 flower_2 - flower
  )
  (:init
    (= (total-cost) 0)
    (at-flower bee_2)
    (at-flower-id bee_2 flower_0)
    (behind-bee bee_1 bee_2)
    (bee-clear bee_1)
    (at-flower bee_0)
    (at-flower-id bee_0 flower_1)
    (bee-clear bee_0)
    (flower-clear flower_2)
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
