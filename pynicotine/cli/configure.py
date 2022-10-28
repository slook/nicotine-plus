from picker import Picker

opts = Picker(
    title = 'Select things',
    options = [
        "one", "two", "three"
    ]
).getSelected()

if opts == False:
    print( "Aborted!" )
else:
    print( opts )
