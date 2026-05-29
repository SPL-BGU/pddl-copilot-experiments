(define (problem kitchen-line-p04)
(:domain kitchen-line)
(:objects
	chef0 - chef
	utensil0 - utensil
	utensil1 - utensil
	utensil2 - utensil
	chef1 - chef
	utensil3 - utensil
	chef2 - chef
	utensil4 - utensil
	utensil5 - utensil
	griddle0 - garnish
	plating1 - garnish
	entree1 - recipe
	entree2 - recipe
	pantry0 - recipe
	dessert3 - recipe
	dessert4 - recipe
	dessert5 - recipe
	appetiser6 - recipe
	entree7 - recipe
)
(:init
	(prepares utensil0 plating1)
	(prepares utensil0 griddle0)
	(sharpening_recipe utensil0 entree2)
	(prepares utensil1 plating1)
	(sharpening_recipe utensil1 entree1)
	(prepares utensil2 plating1)
	(sharpening_recipe utensil2 entree2)
	(carries utensil0 chef0)
	(carries utensil1 chef0)
	(carries utensil2 chef0)
	(energy_spare chef0)
	(focused_on chef0 appetiser6)
	(prepares utensil3 griddle0)
	(sharpening_recipe utensil3 entree2)
	(carries utensil3 chef1)
	(energy_spare chef1)
	(focused_on chef1 pantry0)
	(prepares utensil4 plating1)
	(sharpening_recipe utensil4 pantry0)
	(prepares utensil5 plating1)
	(sharpening_recipe utensil5 pantry0)
	(carries utensil4 chef2)
	(carries utensil5 chef2)
	(energy_spare chef2)
	(focused_on chef2 dessert4)
)
(:goal (and
	(focused_on chef1 dessert5)
	(focused_on chef2 dessert4)
	(have_dish dessert3 griddle0)
	(have_dish dessert4 griddle0)
	(have_dish dessert5 griddle0)
	(have_dish appetiser6 griddle0)
	(have_dish entree7 plating1)
))

)
