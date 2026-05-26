(define (problem strips-sat-x-1)
(:domain kitchen-line)
(:objects
	chef0 - chef
	utensil0 - utensil
	chef1 - chef
	utensil1 - utensil
	griddle0 - garnish
	entree0 - recipe
	pantry1 - recipe
	appetiser2 - recipe
	entree3 - recipe
	entree4 - recipe
)
(:init
	(prepares utensil0 griddle0)
	(sharpening_recipe utensil0 entree0)
	(carries utensil0 chef0)
	(energy_spare chef0)
	(focused_on chef0 pantry1)
	(prepares utensil1 griddle0)
	(sharpening_recipe utensil1 pantry1)
	(carries utensil1 chef1)
	(energy_spare chef1)
	(focused_on chef1 appetiser2)
)
(:goal (and
	(have_dish appetiser2 griddle0)
	(have_dish entree3 griddle0)
	(have_dish entree4 griddle0)
))

)
