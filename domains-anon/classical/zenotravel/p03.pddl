(define (problem bush-expedition-p03)
(:domain bush-expedition)
(:objects
  jeep1 - jeep
  jeep2 - jeep
  jeep3 - jeep
  tourist1 - tourist
  tourist2 - tourist
  waterhole0 - waterhole
  waterhole1 - waterhole
  waterhole2 - waterhole
  range0 - range
  range1 - range
  range2 - range
  range3 - range
  range4 - range
  range5 - range
  range6 - range
  )
(:init
  (resting-at jeep1 waterhole2)
  (tank-level jeep1 range1)
  (resting-at jeep2 waterhole2)
  (tank-level jeep2 range1)
  (resting-at jeep3 waterhole1)
  (tank-level jeep3 range0)
  (resting-at tourist1 waterhole1)
  (resting-at tourist2 waterhole2)
  (follows range0 range1)
  (follows range1 range2)
  (follows range2 range3)
  (follows range3 range4)
  (follows range4 range5)
  (follows range5 range6)
)
(:goal (and
  (resting-at tourist1 waterhole2)
  (resting-at tourist2 waterhole1)
  ))

)
