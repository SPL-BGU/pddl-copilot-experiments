(define   (problem apiary-p05)
  (:domain apiary)
  (:objects
     bee_0  bee_1  bee_2  bee_3  bee_4 - bee
     flower_0 flower_1 flower_2 flower_3 flower_4 - flower
  )
  (:init
    (= (total-cost) 0)
    (at-flower bee_0)
    (at-flower-id bee_0 flower_0)
    (behind-bee bee_2 bee_0)
    (bee-clear bee_2)
    (at-flower bee_3)
    (at-flower-id bee_3 flower_1)
    (bee-clear bee_3)
    (at-flower bee_1)
    (at-flower-id bee_1 flower_2)
    (bee-clear bee_1)
    (at-flower bee_4)
    (at-flower-id bee_4 flower_3)
    (bee-clear bee_4)
    (flower-clear flower_4)
  )
  (:goal
    (and
      (at-flower-id bee_0 flower_0)
      (at-flower-id bee_1 flower_1)
      (at-flower-id bee_2 flower_2)
      (at-flower-id bee_3 flower_3)
      (at-flower-id bee_4 flower_4)
    )
  )
(:metric minimize (total-cost))
)
; =========== INIT ===========
;  curb_0: car_0 car_2
;  curb_1: car_3
;  curb_2: car_1
;  curb_3: car_4
;  curb_4:
; ========== /INIT ===========

; =========== GOAL ===========
;  curb_0: car_0
;  curb_1: car_1
;  curb_2: car_2
;  curb_3: car_3
;  curb_4: car_4
; =========== /GOAL ===========
