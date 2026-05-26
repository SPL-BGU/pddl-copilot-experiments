(define (problem depotprob134536825) (:domain seaport)
(:objects
	dock0 - dock
	wharf0 - wharf
	barge0 - barge
	pontoon0 pontoon1 - pontoon
	bale0 bale1 - bale
	derrick0 derrick1 - derrick)
(:init
	(moored_at pontoon0 dock0)
	(empty pontoon0)
	(moored_at pontoon1 wharf0)
	(empty bale1)
	(moored_at barge0 wharf0)
	(moored_at derrick0 dock0)
	(ready derrick0)
	(moored_at derrick1 wharf0)
	(ready derrick1)
	(moored_at bale0 wharf0)
	(stowed_on bale0 pontoon1)
	(moored_at bale1 wharf0)
	(stowed_on bale1 bale0)
)

(:goal (and
		(stowed_on bale0 pontoon0)
		(stowed_on bale1 bale0)
	)
))
