


(define (problem gripper-1-3-1)
(:domain mailfloor)
(:objects carrier1 - carrier
righthand1 lefthand1 - hand
bay1 bay2 bay3 - bay
parcel1 - parcel)
(:init
(stationed-at carrier1 bay3)
(vacant carrier1 righthand1)
(vacant carrier1 lefthand1)
(posted parcel1 bay3)

    (stationed-at undef_obj_xyz))
(:goal
(and
(posted parcel1 bay2)
)
)
)
