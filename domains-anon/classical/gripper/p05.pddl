


(define (problem mailfloor-p05)
(:domain mailfloor)
(:objects carrier1 carrier2 carrier3 - carrier
righthand1 lefthand1 righthand2 lefthand2 righthand3 lefthand3 - hand
bay1 bay2 bay3 bay4 bay5 - bay
parcel1 parcel2 parcel3 parcel4 parcel5 - parcel)
(:init
(stationed-at carrier1 bay5)
(vacant carrier1 righthand1)
(vacant carrier1 lefthand1)
(stationed-at carrier2 bay1)
(vacant carrier2 righthand2)
(vacant carrier2 lefthand2)
(stationed-at carrier3 bay1)
(vacant carrier3 righthand3)
(vacant carrier3 lefthand3)
(posted parcel1 bay2)
(posted parcel2 bay4)
(posted parcel3 bay1)
(posted parcel4 bay1)
(posted parcel5 bay5)
)
(:goal
(and
(posted parcel1 bay2)
(posted parcel2 bay2)
(posted parcel3 bay3)
(posted parcel4 bay2)
(posted parcel5 bay1)
)
)
)
