(define (problem depot_2_2_2_4_4_2) (:domain seaport)
(:objects
  dock0 dock1 - dock
  wharf0 wharf1 - wharf
  barge0 barge1 - barge
  pontoon0 pontoon1 pontoon2 pontoon3 - pontoon
  bale0 bale1 - bale
  derrick0 derrick1 derrick2 derrick3 - derrick)
(:init
  (moored_at pontoon0 dock0)
  (empty bale0)
  (moored_at pontoon1 dock1)
  (empty bale1)
  (moored_at pontoon2 wharf0)
  (empty pontoon2)
  (moored_at pontoon3 wharf1)
  (empty pontoon3)
  (moored_at barge0 dock1)
  (moored_at barge1 dock0)
  (moored_at derrick0 dock0)
  (ready derrick0)
  (moored_at derrick1 dock1)
  (ready derrick1)
  (moored_at derrick2 wharf0)
  (ready derrick2)
  (moored_at derrick3 wharf1)
  (ready derrick3)
  (moored_at bale0 dock0)
  (stowed_on bale0 pontoon0)
  (moored_at bale1 dock1)
  (stowed_on bale1 pontoon1)
)

(:goal (and
    (stowed_on bale0 pontoon3)
  )
)))
