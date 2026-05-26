(define (problem depotprob134536825) (:domain seaport)
(:objects
	dock0 dock1 - dock
	wharf0 wharf1 - wharf
	barge0 - barge
	pontoon0 pontoon1 pontoon2 pontoon3 - pontoon
	bale0 bale1 bale2 - bale
	derrick0 derrick1 derrick2 derrick3 - derrick)
(:init
	(moored_at pontoon0 dock0)
	(empty bale2)
	(moored_at pontoon1 dock1)
	(empty pontoon1)
	(moored_at pontoon2 wharf0)
	(empty pontoon2)
	(moored_at pontoon3 wharf1)
	(empty bale1)
	(moored_at barge0 wharf0)
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
	(moored_at bale1 wharf1)
	(stowed_on bale1 pontoon3)
	(moored_at bale2 dock0)
	(stowed_on bale2 bale0)
)

(:goal (and
		(stowed_on bale1 pontoon1)
		(stowed_on bale2 bale1)
	)
))
