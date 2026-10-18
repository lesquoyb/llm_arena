# Objects and Classes
> LeekScript

Welcome to the documentation on **object-oriented programming** (**OOP**), which consists of creating classes and objects to organize your code. This feature has been available since LeekScript 2.

## Objects

Objects are values that group several values, each associated with a name. These values are called **properties** or **fields**.

### Creating an object

To create an object, use the following syntax:

```leekscript
var object = { name: "Serge", age: 18 }
```
In this example, the object `object` has two properties, `name` and `age`.

To create an empty object:
```leekscript
var o = {}
```

### Accessing a property

The dot `.` gives access to a property of an object:

```leekscript
var age = object.age
```

There is an alternative syntax, `object["prop"]`, which lets you use a string value to access a property:
```leekscript
var age = object["age"]
var props = ["name", "age"]
for (var prop in props) {
	debug(object[prop])
}
```

### Modifying a property

Once accessed, a property can be modified like a normal variable:

```leekscript
object.name = "Daniel"
object.age += 10
```

### Comparing objects

The `==` and `===` operators only check whether both sides are the same object. They return `false` even if the two objects have the same properties:

```leekscript
var object1 = { a: 5, b: 12 }
var object2 = { a: 5, b: 12 }
debug(object1 == object1) // true
debug(object1 == object2) // false
```

Note: `===` is deprecated as of LeekScript 4 (corpus/language/version-4.md), because `==` is strict there (for example, `null == 0` is no longer true).

### List of properties

```leekscript
var props = object.keys()
// props is an array equal to ["name", "age"]
```

## Classes

A class is a template for creating objects.

### Defining a class

Here is how to define a `Weapon` class with 4 named fields:

```leekscript
class Weapon {
	id
	name
	cost
	damage
}
```

### Creating an object with a class

```leekscript
class Weapon { ... }
var weapon = new Weapon()
```
The `new` keyword is actually optional: a class works like a function and can be called directly to create an object:
```leekscript
var weapon = Weapon()
```

You can get the class of an object with `.class`:
```leekscript
debug(weapon.class) // <class Weapon>
```

### List of fields

```leekscript
var fields = Weapon.fields
// fields is an array equal to ["id", "name", "cost", "damage"]
```

### instanceof

The `instanceof` keyword checks whether an object is an instance of a class:
```leekscript
var weapon = new Weapon()
weapon instanceof Weapon // true
weapon instanceof Chip // false
```

### Constructor

A constructor is a function defined in a class that creates an object from a list of parameters. You define a constructor like this:
```leekscript
class Weapon {
	id
	name
	cost
	damage
	// Constructor with 1 parameter
	constructor(id) {
		this.id = id
		this.name = getWeaponName(id)
		this.cost = getWeaponCost(id)
	}
	// Constructor with 4 parameters
	constructor(id, name, cost, damage) {
		this.id = id
		this.name = name
		this.cost = cost
		this.damage = damage
	}
}
```

Using a constructor:
```leekscript
var weapon1 = new Weapon() // default constructor
var weapon2 = new Weapon(37) // constructor with 1 parameter
var weapon3 = new Weapon(47, "M-Laser", 8, 95) // constructor with 4 parameters
var weapon4 = new Weapon(1, 2) // error: there is no constructor with 2 parameters
```

### Method

A method is a function defined in a class that can be used on any object of that class. You define a method like this:

```leekscript
class Weapon {
	id
	shoot(target) {
		setWeapon(this.id)
		useWeapon(target)
	}
}
```

You call a method with this syntax:
```leekscript
var weapon = new Weapon(WEAPON_PISTOL);
weapon.shoot(getNearestEnemy());
```

The `object["member"]` syntax also works:
```leekscript
weapon["shoot"](getNearestEnemy());
```
It is not recommended, though: it is quite easy to make a mistake with it.

> **Note:** methods can also use Annotations.

### Overloading

You can overload methods simply by changing the number of parameters:
```leekscript
class Weapon {
	id
	shoot(target) {
		setWeapon(this.id);
		useWeapon(target);
	}
	// Overload of the shoot method, with a second optional parameter giving the number of shots.
	shoot(target, shotCount) {
		setWeapon(this.id);
		var i = 1;
		while (i <= shotCount) {
			useWeapon(target);
			i++;
		}
	}
}
```

You can then call the method with either one or two parameters:
```leekscript
var weapon = new Weapon(WEAPON_PISTOL);
// shoots only once
weapon.shoot(getNearestEnemy());
// shoots 3 times
weapon.shoot(getNearestEnemy(), 3);
```

### Inheritance

Inheritance lets you create a hierarchy of classes, using the `extends` keyword. The idea is to declare a "base" class from which other classes can be built. Classes that inherit from it receive all the members (variables) and methods (functions) of the base class, and can redefine them or add new ones.

```leekscript
class Item {
	id
	name
	cost
	damage
}
class Weapon extends Item {
	// Weapon has the same members as Item
}
class Chip extends Item {
	cooldown
	// Chip has the same members as Item, plus a cooldown member
}
```

In this example, the parent class `Item` has two child classes, `Weapon` and `Chip`. Item has 4 members (id, name, cost and damage), which are present in both child classes. But `Chip` has a 5th field, `cooldown`, specific to chips.

If you instantiate these three classes and display the objects, you can see the members of each class:
```leekscript
debug( new Item() );	// displays {id: null, name: null, cost: null, damage: null}
debug( new Weapon() );	// displays {id: null, name: null, cost: null, damage: null}
debug( new Chip() );	// displays {id: null, name: null, cost: null, damage: null, cooldown: null}
```
Our Chip class added a cooldown member, so it only appears in its own instances and not in the others!

A child class also has the type of its base class.
For example, if an object is an instance of the `Weapon` class, it is also an instance of the `Item` class:
```leekscript
var weapon = new Weapon()
weapon instanceof Weapon // true
weapon instanceof Chip // false
weapon instanceof Item // true
```

Child classes also inherit the methods of the parent class.
To call a parent constructor:
```leekscript
class Item {
	constructor() {
		debug("Item constructor!");
	}
}
class Weapon extends Item {
	constructor() {
		debug("Weapon constructor!");
		super() // Calls Item's constructor
	}
}
var weapon = new Weapon();
// Output:
// "Weapon constructor!"
// "Item constructor!"
```
To call a parent method:
```leekscript
class Item {
	use() {
		debug("Use Item!");
	}
}
class Weapon extends Item {
	use() {
		super.use() // Calls Item's use method
		debug("Use Weapon!");
	}
}
var weapon = new Weapon();
// Output:
// "Use Item!"
// "Use Weapon!"
```
If you redefine a method without calling the parent method with super, the base implementation is completely replaced.

A quick example to sum it all up:
```leekscript
class Item {
	id
	constructor(_id) {
		this.id = _id
	}
	get_name() {
		return getChipName(this.id);	// we assume a chip is stored here
	}
	get_cooldown() {
		debugE("Item's get_cooldown() method must be overridden!");
	}
}
class Weapon extends Item {
	// no constructor: Item's constructor will be called directly
	get_name() {
		return getWeaponName(this.id);	// no super(): this simply replaces Item's get_name() function
	}
	get_cooldown() {
		return 0;
	}
}
class Chip extends Item {
	cooldown
	constructor(id) {
		super(id)	// calls Item's constructor
		this.cooldown = getChipCooldown(id)
	}
	// no need to rewrite get_name: Item's get_name method will be called directly
	get_cooldown() {
		return cooldown;
	}
}

var weapon = new Weapon(WEAPON_PISTOL);
var chip = new Chip(CHIP_STALACTITE);

debug("Name: " + weapon.get_name());	// displays "Name: pistol"
debug("Name: " + chip.get_name());	// displays "Name: stalactite"
debug(weapon.get_cooldown());	// displays "0"
debug(chip.get_cooldown());		// displays "3"
```

### Access levels

You can set an access level for each member of a class. There are 3 possible access levels: `public` (the default), `protected` and `private`.

- `public` (default): the member can be accessed directly, by anyone.
- `protected`: the member can only be accessed in the class and its child classes.
- `private`: the member can only be accessed in the class itself.

### Static members

A static member (field or method) is a member that belongs to the class itself rather than to an object of the class.

Static fields are initialized only once (on the first turn), like global variables.

Defining a static field:
```leekscript
class Action {
	public static counter = 0
	constructor() {
		class.counter++
	}
}
new Action()
new Action()
debug(Action.counter) // 2
```

Static method:
```leekscript
class Action {
	public static create() {
		return new Action()
	}
}
var action = Action.create()
```

### Final property

To make a class member read-only, so that it cannot be modified, use the `final` keyword. Such a member can only be initialized where it is declared or in the constructor.

```leekscript
class Action {
	final item;

	constructor(_item) {
		this.item = _item;
	}

	setItem(_item) {
		this.item = _item // Error
	}

	getItem() {
		return this.item
	}
}
```

### string() method

If a class has a string() method, it is called automatically whenever the object needs to be converted to a string:

```leekscript
class Action {
	id
	constructor(_id) {
		this.id = _id
	}
	public string() {
		return "Super action <" + this.id + ">"
	}
}
var action = new Action(12)
debug(action) // Displays "Super action <12>"
```

> **Note:** you can define a string method with default parameters; however, when the object is concatenated, the method is called without arguments.

> **Note 2:** when a class has no string() method but has a parent class, the parent's method is used. That is why it can be useful to use `this.class.name` instead of hard-coding the class name.
