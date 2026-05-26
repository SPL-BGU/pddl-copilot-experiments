(define   (problem apiary-p04)
  (:domain apiary)
  (:objects
     bee_0  bee_1  bee_2  bee_3  bee_4 - bee
     flower_0 flower_1 flower_2 flower_3 - flower
  )
  (:init
    (= (total-cost) 0)
    (at-flower bee_2)
    (at-flower-id bee_2 flower_0)
    (behind-bee bee_3 bee_2)
    (bee-clear bee_3)
    (at-flower bee_1)
    (at-flower-id bee_1 flower_1)
    (behind-bee bee_4 bee_1)
    (bee-clear bee_4)
    (at-flower bee_0)
    (at-flower-id bee_0 flower_2)
    (bee-clear bee_0)
    (flower-clear flower_3)
  )
  (:goal
    (and
      (at-flower-id bee_0 flower_0)
      (behind-bee bee_4 bee_0)
      (at-flower-id bee_1 flower_1)
      (at-flower-id bee_2 flower_2)
      (at-flower-id bee_3 flower_3)
    )
  )
(:metric minimize (total-cost))
)
; =========== INIT ===========
;  curb_0: car_2 car_3
;  curb_1: car_1 car_4
;  curb_2: car_0
;  curb_3:
; ========== /INIT ===========

; =========== GOAL ===========
;  curb_0: car_0 car_4
;  curb_1: car_1
;  curb_2: car_2
;  curb_3: car_3
; =========== /GOAL ===========
