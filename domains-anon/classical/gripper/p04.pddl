


(define (problem gripper-2-5-4)
(:domain mailfloor)
(:objects carrier1 carrier2 - carrier
righthand1 lefthand1 righthand2 lefthand2 - hand
bay1 bay2 bay3 bay4 bay5 - bay
parcel1 parcel2 parcel3 parcel4 - parcel)
(:init
(stationed-at carrier1 bay4)
(vacant carrier1 righthand1)
(vacant carrier1 lefthand1)
(stationed-at carrier2 bay2)
(vacant carrier2 righthand2)
(vacant carrier2 lefthand2)
(posted parcel1 bay2)
(posted parcel2 bay1)
(posted parcel3 bay2)
(posted parcel4 bay2)
)
(:goal
(and
(posted parcel1 bay5)
(posted parcel2 bay4)
(posted parcel3 bay1)
(posted parcel4 bay2)
)
)
)
