# LeekScript 4 — API figée de l'arène

Moteur : `b99a174dd938260d9e47b2e65a208cb32230e26e`.

Signatures extraites du moteur compilé. Les arguments sont positionnels ; leurs noms et leur sémantique ne sont pas inclus.
Les coûts indiquent la base déclarée ; 0 ne signifie pas gratuit (coût calculé ailleurs).

## Fonctions

### abs

Espace : Number. Coût de base déclaré : 1 opérations.

- `abs[real] => real`
- `abs[integer] => integer`
- `abs[big_integer] => big_integer`

### acos

Espace : Number. Coût de base déclaré : 3 opérations.

- `acos[real] => real`

### arrayChunk

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayChunk[Array, integer] => Array`

### arrayClear

Espace : Array. Coût de base déclaré : 1 opérations.

- `arrayClear[Array] => Array`

### arrayConcat

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayConcat[Array, Array] => Array`

### arrayEvery

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayEvery[Array, Function<any, integer, Array => boolean>] => boolean`

### arrayFilter

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayFilter[Array, Function<any, integer, Array => boolean>] => Array`

### arrayFind

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayFind[Array, Function<any, integer, Array => boolean>] => any`

### arrayFlatten

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayFlatten[Array, integer] => Array`
- `arrayFlatten[Array] => Array`

### arrayFoldLeft

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayFoldLeft[Array, Function<any, any, integer, Array => any>, any] => any`

### arrayFoldRight

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayFoldRight[Array, Function<any, any, integer, Array => any>, any] => any`

### arrayFrequencies

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayFrequencies[Array] => Map`

### arrayGet

Espace : Array. Coût de base déclaré : 1 opérations.

- `arrayGet[Array, integer, any] => any`
- `arrayGet[Array, integer] => any`

### arrayIter

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayIter[Array, Function<any, integer, Array => any>] => void`

### arrayMap

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayMap[Array, Function<any, integer, Array => any>] => Array`

### arrayMax

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayMax[Array] => any`

### arrayMin

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayMin[Array] => any`

### arrayPartition

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayPartition[Array, Function<any, integer, Array => boolean>] => Array`

### arrayRandom

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayRandom[Array, integer] => Array`
- `arrayRandom[Array] => Array`

### arrayRemoveAll

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayRemoveAll[Array, any] => void`

### arraySlice

Espace : Array. Coût de base déclaré : 0 opérations.

- `arraySlice[Array, any, any, integer] => Array`
- `arraySlice[Array, any, any] => Array`
- `arraySlice[Array, any] => Array`

### arraySome

Espace : Array. Coût de base déclaré : 0 opérations.

- `arraySome[Array, Function<any, integer, Array => boolean>] => boolean`

### arraySort

Espace : Array. Coût de base déclaré : 0 opérations.

- `arraySort[Array, Function<any, any => real | integer>] => Array`
- `arraySort[Array] => Array`

### arrayToSet

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayToSet[Array] => Set`

### arrayUnique

Espace : Array. Coût de base déclaré : 0 opérations.

- `arrayUnique[Array] => Array`

### asin

Espace : Number. Coût de base déclaré : 3 opérations.

- `asin[real] => real`

### atan

Espace : Number. Coût de base déclaré : 3 opérations.

- `atan[real] => real`

### atan2

Espace : Number. Coût de base déclaré : 4 opérations.

- `atan2[real, real] => real`

### average

Espace : Array. Coût de base déclaré : 0 opérations.

- `average[Array] => real`

### binString

Espace : Number. Coût de base déclaré : 9 opérations.

- `binString[integer] => string`
- `binString[big_integer] => string`

### bitCount

Espace : Number. Coût de base déclaré : 1 opérations.

- `bitCount[integer] => integer`
- `bitCount[big_integer] => integer`

### bitLength

Espace : Number. Coût de base déclaré : 1 opérations.

- `bitLength[integer] => integer`
- `bitLength[big_integer] => integer`

### bitReverse

Espace : Number. Coût de base déclaré : 1 opérations.

- `bitReverse[integer] => integer`

### bitsToReal

Espace : Number. Coût de base déclaré : 3 opérations.

- `bitsToReal[integer] => real`

### byteReverse

Espace : Number. Coût de base déclaré : 1 opérations.

- `byteReverse[integer] => integer`

### canUseChip

Espace : Chip. Coût de base déclaré : 45 opérations.

- `canUseChip[integer, integer] => boolean`

### canUseChipOnCell

Espace : Chip. Coût de base déclaré : 45 opérations.

- `canUseChipOnCell[integer, integer] => boolean`

### canUseWeapon

Espace : Weapon. Coût de base déclaré : 45 opérations.

- `canUseWeapon[integer?, integer?] => boolean`
- `canUseWeapon[integer?] => boolean`

### canUseWeaponOnCell

Espace : Weapon. Coût de base déclaré : 45 opérations.

- `canUseWeaponOnCell[integer?, integer?] => boolean`
- `canUseWeaponOnCell[integer?] => boolean`

### cbrt

Espace : Number. Coût de base déclaré : 5 opérations.

- `cbrt[real] => real`

### ceil

Espace : Number. Coût de base déclaré : 1 opérations.

- `ceil[real] => integer`
- `ceil[integer] => integer`

### charAt

Espace : String. Coût de base déclaré : 4 opérations.

- `charAt[string, integer] => string`

### chipNeedLos

Espace : Chip. Coût de base déclaré : 10 opérations.

- `chipNeedLos[integer] => boolean`

### clearMarks

Espace : Util. Coût de base déclaré : 15 opérations.

- `clearMarks[] => void`

### clone

Espace : Value. Coût de base déclaré : 0 opérations.

- `clone[any, integer] => any`
- `clone[any] => any`

### codePointAt

Espace : String. Coût de base déclaré : 1 opérations.

- `codePointAt[string, integer] => integer`
- `codePointAt[string] => integer`

### contains

Espace : String. Coût de base déclaré : 0 opérations.

- `contains[string, string] => boolean`

### cos

Espace : Number. Coût de base déclaré : 3 opérations.

- `cos[real] => real`

### count

Espace : Array. Coût de base déclaré : 1 opérations.

- `count[Array] => integer`

### debug

Espace : System. Coût de base déclaré : 100 opérations.

- `debug[any] => void`

### debugC

Espace : System. Coût de base déclaré : 100 opérations.

- `debugC[any, integer] => void`

### debugE

Espace : System. Coût de base déclaré : 100 opérations.

- `debugE[any] => void`

### debugW

Espace : System. Coût de base déclaré : 100 opérations.

- `debugW[any] => void`

### deleteRegister

Espace : Util. Coût de base déclaré : 16 opérations.

- `deleteRegister[string] => void`

### endsWith

Espace : String. Coût de base déclaré : 0 opérations.

- `endsWith[string, string] => boolean`

### exp

Espace : Number. Coût de base déclaré : 2 opérations.

- `exp[real] => real`

### fill

Espace : Array. Coût de base déclaré : 0 opérations.

- `fill[Array, any, integer] => void`
- `fill[Array, any] => void`

### floor

Espace : Number. Coût de base déclaré : 1 opérations.

- `floor[real] => integer`
- `floor[integer] => integer`

### getAIID

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getAIID[integer?] => integer?`
- `getAIID[] => integer`

### getAIName

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getAIName[integer?] => string?`
- `getAIName[] => string`

### getAbsoluteShield

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getAbsoluteShield[integer?] => integer?`
- `getAbsoluteShield[] => integer`

### getAgility

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getAgility[integer?] => integer?`
- `getAgility[] => integer`

### getAliveAllies

Espace : Fight. Coût de base déclaré : 100 opérations.

- `getAliveAllies[] => Array<integer>`

### getAliveAlliesCount

Espace : Fight. Coût de base déclaré : 100 opérations.

- `getAliveAlliesCount[] => integer`

### getAliveEnemies

Espace : Fight. Coût de base déclaré : 100 opérations.

- `getAliveEnemies[] => Array<integer>`

### getAliveEnemiesCount

Espace : Fight. Coût de base déclaré : 25 opérations.

- `getAliveEnemiesCount[] => integer`

### getAllChips

Espace : Chip. Coût de base déclaré : 200 opérations.

- `getAllChips[] => Array<integer>`

### getAllEffects

Espace : Fight. Coût de base déclaré : 200 opérations.

- `getAllEffects[] => Array<integer>`

### getAllWeapons

Espace : Weapon. Coût de base déclaré : 200 opérations.

- `getAllWeapons[] => Array<integer>`

### getAlliedTurret

Espace : Fight. Coût de base déclaré : 15 opérations.

- `getAlliedTurret[] => integer?`

### getAllies

Espace : Fight. Coût de base déclaré : 100 opérations.

- `getAllies[] => Array<integer>`

### getAlliesCount

Espace : Fight. Coût de base déclaré : 25 opérations.

- `getAlliesCount[] => integer`

### getAlliesLife

Espace : Fight. Coût de base déclaré : 50 opérations.

- `getAlliesLife[] => integer`

### getAwakeningZone

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getAwakeningZone[integer?] => integer?`
- `getAwakeningZone[] => integer`

### getBirthTurn

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getBirthTurn[integer?] => integer?`
- `getBirthTurn[] => integer`

### getBlue

Espace : Color. Coût de base déclaré : 1 opérations.

- `getBlue[integer] => integer`

### getBulbCharacteristics

Espace : Fight. Coût de base déclaré : 40 opérations.

- `getBulbCharacteristics[integer] => Map`

### getBulbChips

Espace : Fight. Coût de base déclaré : 40 opérations.

- `getBulbChips[integer] => Array?`

### getBulbStats

Espace : Fight. Coût de base déclaré : 40 opérations.

- `getBulbStats[integer] => Map`

### getBulbType

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getBulbType[integer?] => integer?`
- `getBulbType[] => integer`

### getCell

Espace : Entity. Coût de base déclaré : 5 opérations.

- `getCell[integer?] => integer?`
- `getCell[] => integer?`

### getCellContent

Espace : Field. Coût de base déclaré : 6 opérations.

- `getCellContent[integer] => integer`

### getCellDistance

Espace : Field. Coût de base déclaré : 15 opérations.

- `getCellDistance[integer, integer] => integer`

### getCellFromXY

Espace : Field. Coût de base déclaré : 5 opérations.

- `getCellFromXY[integer, integer] => integer?`

### getCellToUseChip

Espace : Fight. Coût de base déclaré : 38080 opérations.

- `getCellToUseChip[integer, integer?, Array<integer>?] => integer`
- `getCellToUseChip[integer, integer?] => integer`

### getCellToUseChipOnCell

Espace : Fight. Coût de base déclaré : 38080 opérations.

- `getCellToUseChipOnCell[integer, integer?, Array<integer>?] => integer`
- `getCellToUseChipOnCell[integer, integer?] => integer`

### getCellToUseWeapon

Espace : Fight. Coût de base déclaré : 38080 opérations.

- `getCellToUseWeapon[integer, integer?, Array<integer>?] => integer`
- `getCellToUseWeapon[integer, integer?] => integer`
- `getCellToUseWeapon[integer] => integer`

### getCellToUseWeaponOnCell

Espace : Fight. Coût de base déclaré : 38080 opérations.

- `getCellToUseWeaponOnCell[integer, integer?, Array<integer>?] => integer`
- `getCellToUseWeaponOnCell[integer, integer?] => integer`
- `getCellToUseWeaponOnCell[integer] => integer`

### getCellX

Espace : Field. Coût de base déclaré : 5 opérations.

- `getCellX[integer] => integer?`

### getCellY

Espace : Field. Coût de base déclaré : 5 opérations.

- `getCellY[integer] => integer?`

### getCellsToUseChip

Espace : Fight. Coût de base déclaré : 25834 opérations.

- `getCellsToUseChip[integer, integer, Array<integer>?] => Array<integer>?`
- `getCellsToUseChip[integer, integer] => Array<integer>?`

### getCellsToUseChipOnCell

Espace : Fight. Coût de base déclaré : 25834 opérations.

- `getCellsToUseChipOnCell[integer, integer, Array<integer>?] => Array<integer>?`
- `getCellsToUseChipOnCell[integer, integer] => Array<integer>?`

### getCellsToUseWeapon

Espace : Fight. Coût de base déclaré : 25834 opérations.

- `getCellsToUseWeapon[integer, integer?, Array<integer>?] => Array<integer>?`
- `getCellsToUseWeapon[integer, integer?] => Array<integer>?`
- `getCellsToUseWeapon[integer] => Array<integer>?`

### getCellsToUseWeaponOnCell

Espace : Fight. Coût de base déclaré : 25834 opérations.

- `getCellsToUseWeaponOnCell[integer, integer, Array<integer>?] => Array<integer>?`
- `getCellsToUseWeaponOnCell[integer, integer] => Array<integer>?`
- `getCellsToUseWeaponOnCell[integer] => Array<integer>?`

### getChestType

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getChestType[integer?] => integer?`
- `getChestType[] => integer`

### getChipArea

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipArea[integer] => integer?`

### getChipCooldown

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipCooldown[integer] => integer`

### getChipCost

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipCost[integer] => integer?`

### getChipEffectiveArea

Espace : Chip. Coût de base déclaré : 78 opérations.

- `getChipEffectiveArea[integer, integer, integer?] => Array<integer>?`
- `getChipEffectiveArea[integer, integer] => Array<integer>?`

### getChipEffects

Espace : Chip. Coût de base déclaré : 125 opérations.

- `getChipEffects[integer] => Array<Array<real | integer>>?`

### getChipFailure

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipFailure[integer] => integer`

### getChipLaunchType

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipLaunchType[integer] => integer?`

### getChipMaxRange

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipMaxRange[integer] => integer?`

### getChipMaxScope

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipMaxScope[integer] => integer?`

### getChipMaxUses

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipMaxUses[integer] => integer?`

### getChipMinRange

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipMinRange[integer] => integer?`

### getChipMinScope

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipMinScope[integer] => integer?`

### getChipName

Espace : Chip. Coût de base déclaré : 15 opérations.

- `getChipName[integer] => string`

### getChipTargets

Espace : Chip. Coût de base déclaré : 40 opérations.

- `getChipTargets[integer, integer] => Array<integer>?`

### getChips

Espace : Entity. Coût de base déclaré : 40 opérations.

- `getChips[integer?] => Array<integer>?`
- `getChips[] => Array<integer>`

### getColor

Espace : Color. Coût de base déclaré : 7 opérations.

- `getColor[integer, integer, integer] => integer`

### getCompositionName

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getCompositionName[integer?] => string?`
- `getCompositionName[] => string`

### getCooldown

Espace : Chip. Coût de base déclaré : 30 opérations.

- `getCooldown[integer, integer?] => integer?`
- `getCooldown[integer] => integer`

### getCores

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getCores[integer?] => integer?`
- `getCores[] => integer`

### getDamageReturn

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getDamageReturn[integer?] => integer?`
- `getDamageReturn[] => integer`

### getDate

Espace : System. Coût de base déclaré : 50 opérations.

- `getDate[] => string`

### getDeadAllies

Espace : Fight. Coût de base déclaré : 100 opérations.

- `getDeadAllies[] => Array<integer>`

### getDeadEnemies

Espace : Fight. Coût de base déclaré : 100 opérations.

- `getDeadEnemies[] => Array<integer>`

### getDeadEnemiesCount

Espace : Fight. Coût de base déclaré : 25 opérations.

- `getDeadEnemiesCount[] => integer`

### getDistance

Espace : Field. Coût de base déclaré : 15 opérations.

- `getDistance[integer, integer] => real`

### getEffects

Espace : Entity. Coût de base déclaré : 25 opérations.

- `getEffects[integer?] => Array<Array<boolean | integer>>?`
- `getEffects[] => Array<Array<boolean | integer>>`

### getEnemies

Espace : Fight. Coût de base déclaré : 100 opérations.

- `getEnemies[] => Array<integer>`

### getEnemiesCount

Espace : Fight. Coût de base déclaré : 25 opérations.

- `getEnemiesCount[] => integer`

### getEnemiesLife

Espace : Fight. Coût de base déclaré : 50 opérations.

- `getEnemiesLife[] => integer`

### getEnemyTurret

Espace : Fight. Coût de base déclaré : 15 opérations.

- `getEnemyTurret[] => integer?`

### getEntity

Espace : Entity. Coût de base déclaré : 5 opérations.

- `getEntity[] => integer`

### getEntityOnCell

Espace : Field. Coût de base déclaré : 15 opérations.

- `getEntityOnCell[integer] => integer`

### getEntityTurnOrder

Espace : Entity. Coût de base déclaré : 30 opérations.

- `getEntityTurnOrder[integer?] => integer?`
- `getEntityTurnOrder[] => integer`

### getFarmerCountry

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getFarmerCountry[integer?] => string?`
- `getFarmerCountry[] => string`

### getFarmerID

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getFarmerID[integer?] => integer?`
- `getFarmerID[] => integer`

### getFarmerName

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getFarmerName[integer?] => string?`
- `getFarmerName[] => string`

### getFarthestAlly

Espace : Fight. Coût de base déclaré : 31 opérations.

- `getFarthestAlly[] => integer`

### getFarthestEnemy

Espace : Fight. Coût de base déclaré : 31 opérations.

- `getFarthestEnemy[] => integer`

### getFightBoss

Espace : Fight. Coût de base déclaré : 10 opérations.

- `getFightBoss[] => integer`

### getFightContext

Espace : Fight. Coût de base déclaré : 10 opérations.

- `getFightContext[] => integer`

### getFightID

Espace : Fight. Coût de base déclaré : 5 opérations.

- `getFightID[] => integer`

### getFightType

Espace : Fight. Coût de base déclaré : 10 opérations.

- `getFightType[] => integer`

### getForce

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getForce[integer?] => integer?`
- `getForce[] => integer`

### getFrequency

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getFrequency[integer?] => integer?`
- `getFrequency[] => integer`

### getGreen

Espace : Color. Coût de base déclaré : 2 opérations.

- `getGreen[integer] => integer`

### getInstructionsCount

Espace : System. Coût de base déclaré : 1 opérations.

- `getInstructionsCount[] => integer`

### getItemUses

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getItemUses[integer] => integer`

### getLaunchedEffects

Espace : Entity. Coût de base déclaré : 25 opérations.

- `getLaunchedEffects[integer?] => Array<Array<boolean | integer>>?`
- `getLaunchedEffects[] => Array<Array<boolean | integer>>`

### getLeekID

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getLeekID[integer?] => integer?`
- `getLeekID[] => integer`

### getLevel

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getLevel[integer?] => integer?`
- `getLevel[] => integer`

### getLife

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getLife[integer?] => integer?`
- `getLife[] => integer`

### getMP

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getMP[integer?] => integer?`
- `getMP[] => integer`

### getMagic

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getMagic[integer?] => integer?`
- `getMagic[] => integer`

### getMapType

Espace : Field. Coût de base déclaré : 5 opérations.

- `getMapType[] => integer`

### getMaxOperations

Espace : System. Coût de base déclaré : 1 opérations.

- `getMaxOperations[] => integer`

### getMaxRAM

Espace : System. Coût de base déclaré : 1 opérations.

- `getMaxRAM[] => integer`

### getMessageAuthor

Espace : Network. Coût de base déclaré : 5 opérations.

- `getMessageAuthor[Array] => integer`

### getMessageParams

Espace : Network. Coût de base déclaré : 5 opérations.

- `getMessageParams[Array] => any`

### getMessageType

Espace : Network. Coût de base déclaré : 5 opérations.

- `getMessageType[Array] => integer`

### getMessages

Espace : Network. Coût de base déclaré : 0 opérations.

- `getMessages[integer] => Array<Array>`
- `getMessages[] => Array<Array>`

### getMobType

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getMobType[integer?] => integer?`
- `getMobType[] => integer`

### getName

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getName[integer?] => string?`
- `getName[] => string`

### getNearestAlly

Espace : Fight. Coût de base déclaré : 25 opérations.

- `getNearestAlly[] => integer`

### getNearestAllyTo

Espace : Fight. Coût de base déclaré : 35 opérations.

- `getNearestAllyTo[integer] => integer?`

### getNearestAllyToCell

Espace : Fight. Coût de base déclaré : 35 opérations.

- `getNearestAllyToCell[integer] => integer?`

### getNearestEnemy

Espace : Fight. Coût de base déclaré : 25 opérations.

- `getNearestEnemy[] => integer`

### getNearestEnemyTo

Espace : Fight. Coût de base déclaré : 35 opérations.

- `getNearestEnemyTo[integer] => integer?`

### getNearestEnemyToCell

Espace : Fight. Coût de base déclaré : 35 opérations.

- `getNearestEnemyToCell[integer] => integer?`

### getNextPlayer

Espace : Fight. Coût de base déclaré : 20 opérations.

- `getNextPlayer[integer?] => integer?`
- `getNextPlayer[] => integer`

### getObstacles

Espace : Field. Coût de base déclaré : 85 opérations.

- `getObstacles[] => Array<integer>`

### getOperations

Espace : System. Coût de base déclaré : 1 opérations.

- `getOperations[] => integer`

### getPassiveEffects

Espace : Entity. Coût de base déclaré : 125 opérations.

- `getPassiveEffects[integer?] => Array<Array<real | integer>>?`
- `getPassiveEffects[] => Array<Array<real | integer>>`

### getPath

Espace : Field. Coût de base déclaré : 0 opérations.

- `getPath[integer, integer, Array?] => Array<integer>?`
- `getPath[integer, integer] => Array<integer>?`

### getPathLength

Espace : Field. Coût de base déclaré : 0 opérations.

- `getPathLength[integer, integer, Array?] => integer?`
- `getPathLength[integer, integer] => integer?`

### getPlantTrigger

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getPlantTrigger[] => integer`

### getPlantType

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getPlantType[integer?] => integer?`
- `getPlantType[] => integer`

### getPower

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getPower[integer?] => integer?`
- `getPower[] => integer`

### getPreviousPlayer

Espace : Fight. Coût de base déclaré : 20 opérations.

- `getPreviousPlayer[integer?] => integer?`
- `getPreviousPlayer[] => integer`

### getRAM

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getRAM[integer?] => integer?`
- `getRAM[] => integer`

### getRed

Espace : Color. Coût de base déclaré : 2 opérations.

- `getRed[integer] => integer`

### getRegister

Espace : Util. Coût de base déclaré : 15 opérations.

- `getRegister[string] => string?`

### getRegisters

Espace : Util. Coût de base déclaré : 25 opérations.

- `getRegisters[] => Map<string, string>`

### getRelativeShield

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getRelativeShield[integer?] => integer?`
- `getRelativeShield[] => integer`

### getResistance

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getResistance[integer?] => integer?`
- `getResistance[] => integer`

### getScience

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getScience[integer?] => integer?`
- `getScience[] => integer`

### getSide

Espace : Entity. Coût de base déclaré : 5 opérations.

- `getSide[integer?] => integer?`
- `getSide[] => integer`

### getStat

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getStat[integer?, integer] => integer?`
- `getStat[integer] => integer`

### getStates

Espace : Entity. Coût de base déclaré : 25 opérations.

- `getStates[integer] => Set<integer>?`
- `getStates[] => Set<integer>`

### getStats

Espace : Entity. Coût de base déclaré : 40 opérations.

- `getStats[integer?] => Map<integer, integer>?`
- `getStats[] => Map<integer, integer>`

### getStrength

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getStrength[integer?] => integer?`
- `getStrength[] => integer`

### getSummoner

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getSummoner[integer?] => integer?`
- `getSummoner[] => integer`

### getSummons

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getSummons[integer?] => Array<integer>`
- `getSummons[] => Array<integer>`

### getTP

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getTP[integer?] => integer?`
- `getTP[] => integer`

### getTeamID

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getTeamID[integer?] => integer?`
- `getTeamID[] => integer`

### getTeamName

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getTeamName[integer?] => string?`
- `getTeamName[] => string`

### getTime

Espace : System. Coût de base déclaré : 50 opérations.

- `getTime[] => string`

### getTimestamp

Espace : System. Coût de base déclaré : 5 opérations.

- `getTimestamp[] => integer`

### getTotalLife

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getTotalLife[integer?] => integer?`
- `getTotalLife[] => integer`

### getTotalMP

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getTotalMP[integer?] => integer?`
- `getTotalMP[] => integer`

### getTotalTP

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getTotalTP[integer?] => integer?`
- `getTotalTP[] => integer`

### getTurn

Espace : Fight. Coût de base déclaré : 15 opérations.

- `getTurn[] => integer`

### getType

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getType[integer?] => integer?`
- `getType[] => integer`

### getUsedRAM

Espace : System. Coût de base déclaré : 1 opérations.

- `getUsedRAM[] => integer`

### getWeapon

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getWeapon[integer?] => integer?`
- `getWeapon[] => integer?`

### getWeaponArea

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponArea[integer] => integer?`

### getWeaponCost

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponCost[integer] => integer`
- `getWeaponCost[] => integer`

### getWeaponEffectiveArea

Espace : Weapon. Coût de base déclaré : 78 opérations.

- `getWeaponEffectiveArea[integer, integer?, integer?] => Array<integer>?`
- `getWeaponEffectiveArea[integer, integer?] => Array<integer>?`
- `getWeaponEffectiveArea[integer] => Array<integer>?`

### getWeaponEffects

Espace : Weapon. Coût de base déclaré : 125 opérations.

- `getWeaponEffects[integer] => Array<Array<real | integer>>?`
- `getWeaponEffects[] => Array<Array<real | integer>>?`

### getWeaponFailure

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponFailure[integer] => integer`
- `getWeaponFailure[] => integer`

### getWeaponLaunchType

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponLaunchType[integer] => integer?`
- `getWeaponLaunchType[] => integer?`

### getWeaponMaxRange

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponMaxRange[integer] => integer`
- `getWeaponMaxRange[] => integer`

### getWeaponMaxUses

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponMaxUses[integer] => integer`
- `getWeaponMaxUses[] => integer`

### getWeaponMinRange

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponMinRange[integer] => integer`
- `getWeaponMinRange[] => integer`

### getWeaponName

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `getWeaponName[integer] => string`
- `getWeaponName[] => string`

### getWeaponPassiveEffects

Espace : Weapon. Coût de base déclaré : 125 opérations.

- `getWeaponPassiveEffects[integer] => Array<Array<real | integer>>`
- `getWeaponPassiveEffects[] => Array<Array<real | integer>>`

### getWeaponTargets

Espace : Weapon. Coût de base déclaré : 40 opérations.

- `getWeaponTargets[integer, integer?] => Array<integer>?`
- `getWeaponTargets[integer] => Array<integer>?`

### getWeapons

Espace : Entity. Coût de base déclaré : 50 opérations.

- `getWeapons[integer?] => Array<integer>?`
- `getWeapons[] => Array<integer>`

### getWinner

Espace : Fight. Coût de base déclaré : 5 opérations.

- `getWinner[] => integer`

### getWisdom

Espace : Entity. Coût de base déclaré : 15 opérations.

- `getWisdom[integer?] => integer?`
- `getWisdom[] => integer`

### hexString

Espace : Number. Coût de base déclaré : 6 opérations.

- `hexString[integer] => string`
- `hexString[big_integer] => string`

### hypot

Espace : Number. Coût de base déclaré : 2 opérations.

- `hypot[real, real] => real`

### inArray

Espace : Array. Coût de base déclaré : 0 opérations.

- `inArray[Array, any] => boolean`

### indexOf

Espace : String. Coût de base déclaré : 0 opérations.

- `indexOf[string, string, integer] => integer`
- `indexOf[string, string] => integer`

### insert

Espace : Array. Coût de base déclaré : 0 opérations.

- `insert[Array, any, integer] => void`

### intervalAverage

Espace : Interval. Coût de base déclaré : 3 opérations.

- `intervalAverage[Interval] => real`

### intervalCombine

Espace : Interval. Coût de base déclaré : 3 opérations.

- `intervalCombine[Interval<real>, Interval<real>] => Interval<real>`
- `intervalCombine[Interval<integer>, Interval<real>] => Interval<real>`
- `intervalCombine[Interval<real>, Interval<integer>] => Interval<real>`
- `intervalCombine[Interval<integer>, Interval<integer>] => Interval<integer>`

### intervalContains

Espace : Interval. Coût de base déclaré : 2 opérations.

- `intervalContains[Interval, integer] => boolean`
- `intervalContains[Interval, real] => boolean`
- `intervalContains[Interval, real | integer] => boolean`

### intervalIntersection

Espace : Interval. Coût de base déclaré : 3 opérations.

- `intervalIntersection[Interval<real>, Interval<real>] => Interval<real>`
- `intervalIntersection[Interval<integer>, Interval<real>] => Interval<real>`
- `intervalIntersection[Interval<real>, Interval<integer>] => Interval<real>`
- `intervalIntersection[Interval<integer>, Interval<integer>] => Interval<integer>`

### intervalIsBounded

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalIsBounded[Interval] => boolean`

### intervalIsClosed

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalIsClosed[Interval] => boolean`

### intervalIsEmpty

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalIsEmpty[Interval] => boolean`

### intervalIsLeftBounded

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalIsLeftBounded[Interval] => boolean`

### intervalIsLeftClosed

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalIsLeftClosed[Interval] => boolean`

### intervalIsRightBounded

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalIsRightBounded[Interval] => boolean`

### intervalIsRightClosed

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalIsRightClosed[Interval] => boolean`

### intervalMax

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalMax[Interval<real>] => real`
- `intervalMax[Interval<integer>] => integer`

### intervalMin

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalMin[Interval<real>] => real`
- `intervalMin[Interval<integer>] => integer`

### intervalSize

Espace : Interval. Coût de base déclaré : 1 opérations.

- `intervalSize[Interval<real>] => real`
- `intervalSize[Interval<integer>] => integer`

### intervalToArray

Espace : Interval. Coût de base déclaré : 0 opérations.

- `intervalToArray[Interval<real>, real] => Array<real>`
- `intervalToArray[Interval<real>] => Array<real>`
- `intervalToArray[Interval<integer>, real] => Array<real>`
- `intervalToArray[Interval<integer>, integer] => Array<integer>`
- `intervalToArray[Interval<integer>] => Array<integer>`

### intervalToSet

Espace : Interval. Coût de base déclaré : 0 opérations.

- `intervalToSet[Interval<real>, real] => Set<real>`
- `intervalToSet[Interval<real>] => Set<real>`
- `intervalToSet[Interval<integer>, real] => Set<real>`
- `intervalToSet[Interval<integer>, integer] => Set<integer>`
- `intervalToSet[Interval<integer>] => Set<integer>`

### isAlive

Espace : Entity. Coût de base déclaré : 15 opérations.

- `isAlive[integer] => boolean`

### isAlly

Espace : Entity. Coût de base déclaré : 15 opérations.

- `isAlly[integer] => boolean`

### isBatchFight

Espace : Fight. Coût de base déclaré : 10 opérations.

- `isBatchFight[] => boolean`

### isChip

Espace : Chip. Coût de base déclaré : 10 opérations.

- `isChip[integer] => boolean`

### isDead

Espace : Entity. Coût de base déclaré : 15 opérations.

- `isDead[integer] => boolean`

### isEmpty

Espace : Array. Coût de base déclaré : 2 opérations.

- `isEmpty[Array] => boolean`

### isEmptyCell

Espace : Field. Coût de base déclaré : 10 opérations.

- `isEmptyCell[integer] => boolean`

### isEnemy

Espace : Entity. Coût de base déclaré : 15 opérations.

- `isEnemy[integer] => boolean`

### isEntity

Espace : Field. Coût de base déclaré : 10 opérations.

- `isEntity[integer] => boolean`

### isFinite

Espace : Number. Coût de base déclaré : 1 opérations.

- `isFinite[real] => boolean`

### isInfinite

Espace : Number. Coût de base déclaré : 1 opérations.

- `isInfinite[real] => boolean`

### isInlineChip

Espace : Chip. Coût de base déclaré : 10 opérations.

- `isInlineChip[integer] => boolean`

### isInlineWeapon

Espace : Weapon. Coût de base déclaré : 10 opérations.

- `isInlineWeapon[integer] => boolean`
- `isInlineWeapon[] => boolean`

### isNaN

Espace : Number. Coût de base déclaré : 1 opérations.

- `isNaN[real] => boolean`

### isObstacle

Espace : Field. Coût de base déclaré : 10 opérations.

- `isObstacle[integer] => boolean`

### isOnSameLine

Espace : Field. Coût de base déclaré : 15 opérations.

- `isOnSameLine[integer, integer] => boolean`

### isPermutation

Espace : Number. Coût de base déclaré : 10 opérations.

- `isPermutation[integer, integer] => boolean`

### isStatic

Espace : Entity. Coût de base déclaré : 15 opérations.

- `isStatic[integer?] => boolean`
- `isStatic[] => boolean`

### isSummon

Espace : Entity. Coût de base déclaré : 10 opérations.

- `isSummon[integer?] => boolean?`
- `isSummon[] => boolean`

### isWeapon

Espace : Weapon. Coût de base déclaré : 15 opérations.

- `isWeapon[integer] => boolean`

### join

Espace : Array. Coût de base déclaré : 0 opérations.

- `join[Array, string] => string`

### jsonDecode

Espace : JSON. Coût de base déclaré : 0 opérations.

- `jsonDecode[string] => any`

### jsonEncode

Espace : JSON. Coût de base déclaré : 0 opérations.

- `jsonEncode[any] => string`

### lama

Espace : Entity. Coût de base déclaré : 30 opérations.

- `lama[] => void`

### leadingZeros

Espace : Number. Coût de base déclaré : 1 opérations.

- `leadingZeros[integer] => integer`

### length

Espace : String. Coût de base déclaré : 1 opérations.

- `length[string] => integer`

### lineOfSight

Espace : Field. Coût de base déclaré : 31 opérations.

- `lineOfSight[integer, integer, null | Array<integer> | integer] => boolean?`
- `lineOfSight[integer, integer] => boolean?`

### listen

Espace : Entity. Coût de base déclaré : 78 opérations.

- `listen[] => Array<Array>`

### log

Espace : Number. Coût de base déclaré : 4 opérations.

- `log[real] => real`

### log10

Espace : Number. Coût de base déclaré : 5 opérations.

- `log10[real] => real`

### log2

Espace : Number. Coût de base déclaré : 5 opérations.

- `log2[real] => real`

### mapAverage

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapAverage[Map] => real`

### mapClear

Espace : Map. Coût de base déclaré : 1 opérations.

- `mapClear[Map] => Map`

### mapContains

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapContains[Map, any] => boolean`

### mapContainsKey

Espace : Map. Coût de base déclaré : 1 opérations.

- `mapContainsKey[Map, any] => boolean`

### mapEvery

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapEvery[Map, Function<any, any, Map => any>] => boolean`

### mapFill

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapFill[Map, any] => void`

### mapFilter

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapFilter[Map, Function<any, any, Map => boolean>] => Map`

### mapFold

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapFold[Map, Function<any, any, any, Map => any>, any] => any`

### mapGet

Espace : Map. Coût de base déclaré : 2 opérations.

- `mapGet[Map, any, any] => any`
- `mapGet[Map, any] => any`

### mapIsEmpty

Espace : Map. Coût de base déclaré : 2 opérations.

- `mapIsEmpty[Map] => boolean`

### mapIter

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapIter[Map, Function<any, any, Map => any>] => void`

### mapKeys

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapKeys[Map] => Array`

### mapMap

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapMap[Map, Function<any, any, Map => any>] => Map`

### mapMax

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapMax[Map] => any`

### mapMerge

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapMerge[Map, Map] => any`

### mapMin

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapMin[Map] => any`

### mapPut

Espace : Map. Coût de base déclaré : 3 opérations.

- `mapPut[Map, any, any] => any`

### mapPutAll

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapPutAll[Map, Map] => void`

### mapRemove

Espace : Map. Coût de base déclaré : 2 opérations.

- `mapRemove[Map, any] => any`

### mapRemoveAll

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapRemoveAll[Map, any] => void`

### mapReplace

Espace : Map. Coût de base déclaré : 3 opérations.

- `mapReplace[Map, any, any] => any`

### mapReplaceAll

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapReplaceAll[Map, Map] => void`

### mapSearch

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapSearch[Map, any] => any`

### mapSize

Espace : Map. Coût de base déclaré : 1 opérations.

- `mapSize[Map] => integer`

### mapSome

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapSome[Map, Function<any, any, Map => any>] => boolean`

### mapSum

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapSum[Map] => real`

### mapValues

Espace : Map. Coût de base déclaré : 0 opérations.

- `mapValues[Map] => Array`

### mark

Espace : Util. Coût de base déclaré : 164 opérations.

- `mark[Array<integer> | integer, integer, integer] => boolean`
- `mark[Array<integer> | integer, integer] => boolean`
- `mark[Array<integer> | integer] => boolean`

### markText

Espace : Util. Coût de base déclaré : 164 opérations.

- `markText[Array<integer> | integer, any, integer, integer] => boolean`
- `markText[Array<integer> | integer, any, integer] => boolean`
- `markText[Array<integer> | integer, any] => boolean`
- `markText[Array<integer> | integer] => boolean`

### max

Espace : Number. Coût de base déclaré : 1 opérations.

- `max[real, real] => real`
- `max[integer, integer] => integer`
- `max[big_integer, big_integer] => big_integer`

### min

Espace : Number. Coût de base déclaré : 1 opérations.

- `min[real, real] => real`
- `min[integer, integer] => integer`
- `min[big_integer, big_integer] => big_integer`

### moveAwayFrom

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveAwayFrom[integer, integer] => integer`
- `moveAwayFrom[integer] => integer`

### moveAwayFromCell

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveAwayFromCell[integer, integer] => integer`
- `moveAwayFromCell[integer] => integer`

### moveAwayFromCells

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveAwayFromCells[Array<integer>, integer] => integer`
- `moveAwayFromCells[Array<integer>] => integer`

### moveAwayFromEntities

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveAwayFromEntities[Array<integer>, integer] => integer`
- `moveAwayFromEntities[Array<integer>] => integer`

### moveAwayFromLeeks

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveAwayFromLeeks[Array<integer>, integer] => integer`
- `moveAwayFromLeeks[Array<integer>] => integer`

### moveAwayFromLine

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveAwayFromLine[integer, integer, integer] => integer`
- `moveAwayFromLine[integer, integer] => integer`

### moveToward

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveToward[integer, integer] => integer`
- `moveToward[integer] => integer`

### moveTowardCell

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveTowardCell[integer, integer] => integer`
- `moveTowardCell[integer] => integer`

### moveTowardCells

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveTowardCells[Array<integer>, integer] => integer`
- `moveTowardCells[Array<integer>] => integer`

### moveTowardEntities

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveTowardEntities[Array<integer>, integer] => integer`
- `moveTowardEntities[Array<integer>] => integer`

### moveTowardLeeks

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveTowardLeeks[Array<integer>, integer] => integer`
- `moveTowardLeeks[Array<integer>] => integer`

### moveTowardLine

Espace : Fight. Coût de base déclaré : 500 opérations.

- `moveTowardLine[integer, integer, integer] => integer`
- `moveTowardLine[integer, integer] => integer`

### number

Espace : Value. Coût de base déclaré : 3 opérations.

- `number[any] => real | integer`

### pause

Espace : Util. Coût de base déclaré : 30 opérations.

- `pause[] => void`

### pop

Espace : Array. Coût de base déclaré : 2 opérations.

- `pop[Array] => any`

### pow

Espace : Number. Coût de base déclaré : 7 opérations.

- `pow[real, real] => real`
- `pow[big_integer, big_integer] => big_integer`

### push

Espace : Array. Coût de base déclaré : 2 opérations.

- `push[Array, any] => void`

### pushAll

Espace : Array. Coût de base déclaré : 0 opérations.

- `pushAll[Array, Array] => void`

### rand

Espace : Number. Coût de base déclaré : 3 opérations.

- `rand[] => real`

### randInt

Espace : Number. Coût de base déclaré : 2 opérations.

- `randInt[integer, integer] => integer`

### randReal

Espace : Number. Coût de base déclaré : 3 opérations.

- `randReal[real, real] => real`

### realBits

Espace : Number. Coût de base déclaré : 1 opérations.

- `realBits[real] => integer`

### remove

Espace : Array. Coût de base déclaré : 0 opérations.

- `remove[Array, integer] => any`

### removeElement

Espace : Array. Coût de base déclaré : 0 opérations.

- `removeElement[Array, any] => void`

### replace

Espace : String. Coût de base déclaré : 0 opérations.

- `replace[string, string, string] => string`

### resurrect

Espace : Chip. Coût de base déclaré : 500 opérations.

- `resurrect[integer, integer] => integer`

### reverse

Espace : Array. Coût de base déclaré : 0 opérations.

- `reverse[Array] => void`

### rotateLeft

Espace : Number. Coût de base déclaré : 1 opérations.

- `rotateLeft[integer, integer] => integer`

### rotateRight

Espace : Number. Coût de base déclaré : 1 opérations.

- `rotateRight[integer, integer] => integer`

### round

Espace : Number. Coût de base déclaré : 1 opérations.

- `round[real] => integer`
- `round[integer] => integer`

### say

Espace : Entity. Coût de base déclaré : 30 opérations.

- `say[any] => boolean`

### search

Espace : Array. Coût de base déclaré : 0 opérations.

- `search[Array, any, integer] => any`
- `search[Array, any] => any`

### sendAll

Espace : Network. Coût de base déclaré : 40 opérations.

- `sendAll[integer, any] => void`

### sendTo

Espace : Network. Coût de base déclaré : 15 opérations.

- `sendTo[integer, integer, any] => boolean`

### setBit

Espace : Number. Coût de base déclaré : 1 opérations.

- `setBit[integer, integer] => integer`
- `setBit[integer, integer, integer] => integer`
- `setBit[integer, integer, boolean] => integer`
- `setBit[big_integer, integer] => big_integer`
- `setBit[big_integer, integer, integer] => big_integer`
- `setBit[big_integer, integer, boolean] => big_integer`

### setClear

Espace : Set. Coût de base déclaré : 1 opérations.

- `setClear[Set] => Set`

### setContains

Espace : Set. Coût de base déclaré : 1 opérations.

- `setContains[Set, any] => boolean`

### setDifference

Espace : Set. Coût de base déclaré : 0 opérations.

- `setDifference[Set, Set] => Set`

### setDisjunction

Espace : Set. Coût de base déclaré : 0 opérations.

- `setDisjunction[Set, Set] => Set`

### setFilter

Espace : Set. Coût de base déclaré : 0 opérations.

- `setFilter[Set, Function<any, Set => boolean>] => Set`

### setIntersection

Espace : Set. Coût de base déclaré : 0 opérations.

- `setIntersection[Set, Set] => Set`

### setIsEmpty

Espace : Set. Coût de base déclaré : 1 opérations.

- `setIsEmpty[Set] => boolean`

### setIsSubsetOf

Espace : Set. Coût de base déclaré : 0 opérations.

- `setIsSubsetOf[Set, Set] => boolean`

### setLoadout

Espace : Fight. Coût de base déclaré : 100 opérations.

- `setLoadout[string] => boolean`
- `setLoadout[string, boolean] => boolean`

### setPut

Espace : Set. Coût de base déclaré : 3 opérations.

- `setPut[Set, any] => boolean`

### setRegister

Espace : Util. Coût de base déclaré : 50 opérations.

- `setRegister[string, any] => boolean`

### setRemove

Espace : Set. Coût de base déclaré : 2 opérations.

- `setRemove[Set, any] => boolean`

### setSize

Espace : Set. Coût de base déclaré : 1 opérations.

- `setSize[Set] => integer`

### setToArray

Espace : Set. Coût de base déclaré : 0 opérations.

- `setToArray[Set] => Array`

### setUnion

Espace : Set. Coût de base déclaré : 0 opérations.

- `setUnion[Set, Set] => Set`

### setWeapon

Espace : Entity. Coût de base déclaré : 15 opérations.

- `setWeapon[integer] => boolean`

### shift

Espace : Array. Coût de base déclaré : 0 opérations.

- `shift[Array] => any`

### show

Espace : Util. Coût de base déclaré : 0 opérations.

- `show[integer, integer] => boolean`
- `show[integer] => boolean`

### shuffle

Espace : Array. Coût de base déclaré : 0 opérations.

- `shuffle[Array] => void`

### signum

Espace : Number. Coût de base déclaré : 1 opérations.

- `signum[real] => integer`
- `signum[integer] => integer`
- `signum[big_integer] => integer`

### sin

Espace : Number. Coût de base déclaré : 3 opérations.

- `sin[real] => real`

### sort

Espace : Array. Coût de base déclaré : 0 opérations.

- `sort[Array, integer] => void`
- `sort[Array] => void`

### split

Espace : String. Coût de base déclaré : 0 opérations.

- `split[string, string, integer] => Array<string>`
- `split[string, string] => Array<string>`

### sqrt

Espace : Number. Coût de base déclaré : 3 opérations.

- `sqrt[real] => real`

### startsWith

Espace : String. Coût de base déclaré : 0 opérations.

- `startsWith[string, string] => boolean`

### string

Espace : Value. Coût de base déclaré : 6 opérations.

- `string[any] => string`

### substring

Espace : String. Coût de base déclaré : 0 opérations.

- `substring[string, integer, integer] => string`
- `substring[string, integer] => string`

### sum

Espace : Array. Coût de base déclaré : 0 opérations.

- `sum[Array] => real`

### summon

Espace : Chip. Coût de base déclaré : 1750 opérations.

- `summon[integer, integer, Function< => any>, string] => integer`
- `summon[integer, integer, Function< => any>] => integer`

### tan

Espace : Number. Coût de base déclaré : 4 opérations.

- `tan[real] => real`

### testBit

Espace : Number. Coût de base déclaré : 1 opérations.

- `testBit[integer, integer] => boolean`
- `testBit[big_integer, integer] => boolean`

### toDegrees

Espace : Number. Coût de base déclaré : 3 opérations.

- `toDegrees[real] => real`

### toFixed

Espace : Number. Coût de base déclaré : 40 opérations.

- `toFixed[real, integer] => string`
- `toFixed[integer, integer] => string`
- `toFixed[big_integer, integer] => string`

### toLower

Espace : String. Coût de base déclaré : 0 opérations.

- `toLower[string] => string`

### toRadians

Espace : Number. Coût de base déclaré : 3 opérations.

- `toRadians[real] => real`

### toUpper

Espace : String. Coût de base déclaré : 0 opérations.

- `toUpper[string] => string`

### trailingZeros

Espace : Number. Coût de base déclaré : 1 opérations.

- `trailingZeros[integer] => integer`
- `trailingZeros[big_integer] => integer`

### trim

Espace : String. Coût de base déclaré : 5 opérations.

- `trim[string] => string`

### typeOf

Espace : Value. Coût de base déclaré : 1 opérations.

- `typeOf[any] => integer`

### unknown

Espace : Value. Coût de base déclaré : 100 opérations.

- `unknown[any] => any`

### unshift

Espace : Array. Coût de base déclaré : 0 opérations.

- `unshift[Array, any] => void`

### useChip

Espace : Chip. Coût de base déclaré : 3000 opérations.

- `useChip[integer, integer] => integer`
- `useChip[integer] => integer`

### useChipOnCell

Espace : Chip. Coût de base déclaré : 3000 opérations.

- `useChipOnCell[integer, integer] => integer`

### useWeapon

Espace : Weapon. Coût de base déclaré : 3000 opérations.

- `useWeapon[integer] => integer`

### useWeaponOnCell

Espace : Weapon. Coût de base déclaré : 3000 opérations.

- `useWeaponOnCell[integer] => integer`

### weaponNeedLos

Espace : Weapon. Coût de base déclaré : 10 opérations.

- `weaponNeedLos[integer] => boolean`
- `weaponNeedLos[] => boolean`

## Constantes

- `AREA_ALLIES` = `15.0`
- `AREA_CIRCLE_1` = `3.0`
- `AREA_CIRCLE_2` = `4.0`
- `AREA_CIRCLE_3` = `5.0`
- `AREA_ENEMIES` = `14.0`
- `AREA_FIRST_INLINE` = `13.0`
- `AREA_LASER_LINE` = `2.0`
- `AREA_PLUS_1` = `3.0`
- `AREA_PLUS_2` = `6.0`
- `AREA_PLUS_3` = `7.0`
- `AREA_POINT` = `1.0`
- `AREA_SQUARE_1` = `11.0`
- `AREA_SQUARE_2` = `12.0`
- `AREA_X_1` = `8.0`
- `AREA_X_2` = `9.0`
- `AREA_X_3` = `10.0`
- `BOSS_EVIL_PUMPKIN` = `3.0`
- `BOSS_FENNEL_KING` = `2.0`
- `BOSS_NASU_SAMOURAI` = `1.0`
- `BOSS_NASU_SAMURAI` = `1.0`
- `BULB_FIRE` = `2.0`
- `BULB_HEALER` = `3.0`
- `BULB_ICED` = `5.0`
- `BULB_LIGHTNING` = `6.0`
- `BULB_METALLIC` = `7.0`
- `BULB_PUNY` = `1.0`
- `BULB_ROCKY` = `4.0`
- `BULB_SAVANT` = `12.0`
- `BULB_TACTICIAN` = `11.0`
- `BULB_WIZARD` = `8.0`
- `CELL_EMPTY` = `0.0`
- `CELL_ENTITY` = `1.0`
- `CELL_OBSTACLE` = `2.0`
- `CELL_PLAYER` = `1.0`
- `CHEST_DIAMOND` = `3.0`
- `CHEST_IRON` = `2.0`
- `CHEST_WOOD` = `1.0`
- `CHIP_ACCELERATION` = `91.0`
- `CHIP_ADRENALINE` = `16.0`
- `CHIP_ALTERATION` = `141.0`
- `CHIP_ANTIDOTE` = `110.0`
- `CHIP_APOCALYPSE` = `418.0`
- `CHIP_ARMOR` = `22.0`
- `CHIP_ARMORING` = `67.0`
- `CHIP_ARSENIC` = `171.0`
- `CHIP_AWAKENING` = `415.0`
- `CHIP_AWEKENING` = `415.0`
- `CHIP_BALL_AND_CHAIN` = `93.0`
- `CHIP_BANDAGE` = `3.0`
- `CHIP_BARK` = `104.0`
- `CHIP_BOXING_GLOVE` = `163.0`
- `CHIP_BRAINWASHING` = `170.0`
- `CHIP_BRAMBLE` = `172.0`
- `CHIP_BURNING` = `105.0`
- `CHIP_CAPSAICIN` = `445.0`
- `CHIP_CARAPACE` = `81.0`
- `CHIP_CHILLI_PEPPER` = `165.0`
- `CHIP_COLLAR` = `103.0`
- `CHIP_CORN` = `164.0`
- `CHIP_COVETOUSNESS` = `120.0`
- `CHIP_COVID` = `152.0`
- `CHIP_CRUSHING` = `169.0`
- `CHIP_CURE` = `4.0`
- `CHIP_DESINTEGRATION` = `160.0`
- `CHIP_DEVIL_STRIKE` = `85.0`
- `CHIP_DIVINE_PROTECTION` = `419.0`
- `CHIP_DOME` = `173.0`
- `CHIP_DOPING` = `26.0`
- `CHIP_DRIP` = `10.0`
- `CHIP_ELEVATION` = `154.0`
- `CHIP_EXASPERATION` = `425.0`
- `CHIP_FEROCITY` = `102.0`
- `CHIP_FERTILIZER` = `90.0`
- `CHIP_FIRE_BALL` = `413.0`
- `CHIP_FIRE_BULB` = `74.0`
- `CHIP_FLAME` = `5.0`
- `CHIP_FLASH` = `6.0`
- `CHIP_FORTRESS` = `29.0`
- `CHIP_FRACTURE` = `106.0`
- `CHIP_GRAPPLE` = `162.0`
- `CHIP_HEALER_BULB` = `75.0`
- `CHIP_HELMET` = `21.0`
- `CHIP_HEMORRHAGE` = `273.0`
- `CHIP_ICE` = `2.0`
- `CHIP_ICEBERG` = `31.0`
- `CHIP_ICED_BULB` = `77.0`
- `CHIP_INVERSION` = `68.0`
- `CHIP_JUMP` = `144.0`
- `CHIP_KEMURIDAMA` = `412.0`
- `CHIP_KILL` = `417.0`
- `CHIP_KNOWLEDGE` = `155.0`
- `CHIP_LEATHER_BOOTS` = `14.0`
- `CHIP_LIBERATION` = `34.0`
- `CHIP_LIGHTNING` = `33.0`
- `CHIP_LIGHTNING_BULB` = `78.0`
- `CHIP_LOAM` = `89.0`
- `CHIP_MANUMISSION` = `174.0`
- `CHIP_MATURATION` = `442.0`
- `CHIP_METALLIC_BULB` = `79.0`
- `CHIP_METEORITE` = `36.0`
- `CHIP_MIRROR` = `101.0`
- `CHIP_MOTIVATION` = `15.0`
- `CHIP_MUTATION` = `159.0`
- `CHIP_PEBBLE` = `19.0`
- `CHIP_PIQUANT` = `444.0`
- `CHIP_PLAGUE` = `99.0`
- `CHIP_PLASMA` = `143.0`
- `CHIP_POPCORN` = `447.0`
- `CHIP_PRECIPITATION` = `122.0`
- `CHIP_PRISM` = `276.0`
- `CHIP_PROTEIN` = `8.0`
- `CHIP_PROTOTAXITE` = `441.0`
- `CHIP_PUNISHMENT` = `114.0`
- `CHIP_PUNY_BULB` = `73.0`
- `CHIP_RAGE` = `17.0`
- `CHIP_RAMPART` = `24.0`
- `CHIP_REFLEXES` = `27.0`
- `CHIP_REGENERATION` = `35.0`
- `CHIP_REMISSION` = `80.0`
- `CHIP_REPOTTING` = `157.0`
- `CHIP_RESURRECTION` = `84.0`
- `CHIP_ROCK` = `7.0`
- `CHIP_ROCKFALL` = `32.0`
- `CHIP_ROCKY_BULB` = `76.0`
- `CHIP_SAVANT_BULB` = `167.0`
- `CHIP_SERUM` = `168.0`
- `CHIP_SEVEN_LEAGUE_BOOTS` = `12.0`
- `CHIP_SHIELD` = `20.0`
- `CHIP_SHOCK` = `1.0`
- `CHIP_SHURIKEN` = `411.0`
- `CHIP_SLOW_DOWN` = `92.0`
- `CHIP_SOLIDIFICATION` = `96.0`
- `CHIP_SOPORIFIC` = `95.0`
- `CHIP_SPARK` = `18.0`
- `CHIP_STALACTITE` = `30.0`
- `CHIP_STEROID` = `25.0`
- `CHIP_STRETCHING` = `9.0`
- `CHIP_SUGAR` = `446.0`
- `CHIP_SUPERINFECTION` = `443.0`
- `CHIP_TACTICIAN_BULB` = `166.0`
- `CHIP_TELEPORTATION` = `59.0`
- `CHIP_THERAPY` = `158.0`
- `CHIP_THORN` = `100.0`
- `CHIP_THUNDER` = `416.0`
- `CHIP_TOXIN` = `98.0`
- `CHIP_TRANQUILIZER` = `94.0`
- `CHIP_TRANSMUTATION` = `161.0`
- `CHIP_TREBUCHET` = `414.0`
- `CHIP_VACCINE` = `11.0`
- `CHIP_VAMPIRIZATION` = `121.0`
- `CHIP_VENOM` = `97.0`
- `CHIP_WALL` = `23.0`
- `CHIP_WARM_UP` = `28.0`
- `CHIP_WHIP` = `88.0`
- `CHIP_WINGED_BOOTS` = `13.0`
- `CHIP_WIZARDRY` = `156.0`
- `CHIP_WIZARD_BULB` = `142.0`
- `COLOR_BLUE` = `255.0`
- `COLOR_GREEN` = `65280.0`
- `COLOR_RED` = `1.671168E7`
- `CRITICAL_FACTOR` = `1.3`
- `E` = `2.718281828459045`
- `EFFECT_ABSOLUTE_SHIELD` = `6.0`
- `EFFECT_ABSOLUTE_VULNERABILITY` = `27.0`
- `EFFECT_ADD_STATE` = `59.0`
- `EFFECT_AFTEREFFECT` = `25.0`
- `EFFECT_AGILITY` = `4.0`
- `EFFECT_ALLY_KILLED_TO_AGILITY` = `55.0`
- `EFFECT_ANTIDOTE` = `23.0`
- `EFFECT_ATTRACT` = `46.0`
- `EFFECT_BOOST_MAX_LIFE` = `12.0`
- `EFFECT_BUFF_ABSOLUTE_SHIELD` = `6.0`
- `EFFECT_BUFF_AGILITY` = `4.0`
- `EFFECT_BUFF_DAMAGE` = `1.0`
- `EFFECT_BUFF_DEBUFF` = `9.0`
- `EFFECT_BUFF_FORCE` = `3.0`
- `EFFECT_BUFF_HEAL` = `2.0`
- `EFFECT_BUFF_MP` = `7.0`
- `EFFECT_BUFF_RELATIVE_SHIELD` = `5.0`
- `EFFECT_BUFF_RESISTANCE` = `21.0`
- `EFFECT_BUFF_STRENGTH` = `3.0`
- `EFFECT_BUFF_TELEPORTATION` = `10.0`
- `EFFECT_BUFF_TP` = `8.0`
- `EFFECT_BUFF_WISDOM` = `22.0`
- `EFFECT_CRITICAL_TO_HEAL` = `58.0`
- `EFFECT_DAMAGE` = `1.0`
- `EFFECT_DAMAGE_RETURN` = `20.0`
- `EFFECT_DAMAGE_TO_ABSOLUTE_SHIELD` = `34.0`
- `EFFECT_DAMAGE_TO_RESISTANCE` = `63.0`
- `EFFECT_DAMAGE_TO_STRENGTH` = `35.0`
- `EFFECT_DEBUFF` = `9.0`
- `EFFECT_FORCE` = `3.0`
- `EFFECT_HEAL` = `2.0`
- `EFFECT_INVERT` = `11.0`
- `EFFECT_KILL` = `16.0`
- `EFFECT_KILL_TO_TP` = `56.0`
- `EFFECT_LIFE_DAMAGE` = `28.0`
- `EFFECT_MODIFIER_IRREDUCTIBLE` = `16.0`
- `EFFECT_MODIFIER_MULTIPLIED_BY_TARGETS` = `2.0`
- `EFFECT_MODIFIER_NOT_REPLACEABLE` = `8.0`
- `EFFECT_MODIFIER_ON_CASTER` = `4.0`
- `EFFECT_MODIFIER_STACKABLE` = `1.0`
- `EFFECT_MOVED_TO_MP` = `50.0`
- `EFFECT_MP` = `7.0`
- `EFFECT_MULTIPLY_STATS` = `62.0`
- `EFFECT_NOVA_DAMAGE` = `30.0`
- `EFFECT_NOVA_DAMAGE_TO_MAGIC` = `36.0`
- `EFFECT_NOVA_VITALITY` = `45.0`
- `EFFECT_POISON` = `13.0`
- `EFFECT_POISON_TO_SCIENCE` = `33.0`
- `EFFECT_PROPAGATION` = `43.0`
- `EFFECT_PUSH` = `51.0`
- `EFFECT_RAW_ABSOLUTE_SHIELD` = `37.0`
- `EFFECT_RAW_BUFF_AGILITY` = `41.0`
- `EFFECT_RAW_BUFF_MAGIC` = `39.0`
- `EFFECT_RAW_BUFF_MP` = `31.0`
- `EFFECT_RAW_BUFF_POWER` = `52.0`
- `EFFECT_RAW_BUFF_RESISTANCE` = `42.0`
- `EFFECT_RAW_BUFF_SCIENCE` = `40.0`
- `EFFECT_RAW_BUFF_STRENGTH` = `38.0`
- `EFFECT_RAW_BUFF_TP` = `32.0`
- `EFFECT_RAW_BUFF_WISDOM` = `44.0`
- `EFFECT_RAW_HEAL` = `57.0`
- `EFFECT_RAW_RELATIVE_SHIELD` = `54.0`
- `EFFECT_RELATIVE_SHIELD` = `5.0`
- `EFFECT_REMOVE_SHACKLES` = `49.0`
- `EFFECT_REPEL` = `53.0`
- `EFFECT_RESURRECT` = `15.0`
- `EFFECT_SHACKLE_AGILITY` = `47.0`
- `EFFECT_SHACKLE_MAGIC` = `24.0`
- `EFFECT_SHACKLE_MP` = `17.0`
- `EFFECT_SHACKLE_STRENGTH` = `19.0`
- `EFFECT_SHACKLE_TP` = `18.0`
- `EFFECT_SHACKLE_WISDOM` = `48.0`
- `EFFECT_SLIDE_TO` = `46.0`
- `EFFECT_STEAL_ABSOLUTE_SHIELD` = `29.0`
- `EFFECT_STEAL_LIFE` = `61.0`
- `EFFECT_SUMMON` = `14.0`
- `EFFECT_SUPERINFECTION` = `64.0`
- `EFFECT_TARGET_ALLIES` = `2.0`
- `EFFECT_TARGET_ALWAYS_CASTER` = `0.0`
- `EFFECT_TARGET_CASTER` = `4.0`
- `EFFECT_TARGET_ENEMIES` = `1.0`
- `EFFECT_TARGET_NON_SUMMONS` = `8.0`
- `EFFECT_TARGET_NOT_CASTER` = `0.0`
- `EFFECT_TARGET_SUMMONS` = `16.0`
- `EFFECT_TELEPORT` = `10.0`
- `EFFECT_TOTAL_DEBUFF` = `60.0`
- `EFFECT_TP` = `8.0`
- `EFFECT_VULNERABILITY` = `26.0`
- `ENTITY_BULB` = `2.0`
- `ENTITY_CHEST` = `4.0`
- `ENTITY_LEEK` = `1.0`
- `ENTITY_MOB` = `5.0`
- `ENTITY_PLANT` = `6.0`
- `ENTITY_TURRET` = `3.0`
- `EROSION_CRITICAL_BONUS` = `0.1`
- `EROSION_DAMAGE` = `0.05`
- `EROSION_POISON` = `0.1`
- `FIGHT_CONTEXT_BATTLE_ROYALE` = `5.0`
- `FIGHT_CONTEXT_CHALLENGE` = `1.0`
- `FIGHT_CONTEXT_GARDEN` = `2.0`
- `FIGHT_CONTEXT_TEST` = `0.0`
- `FIGHT_CONTEXT_TOURNAMENT` = `3.0`
- `FIGHT_TYPE_BATTLE_ROYALE` = `3.0`
- `FIGHT_TYPE_BOSS` = `4.0`
- `FIGHT_TYPE_CHEST_HUNT` = `6.0`
- `FIGHT_TYPE_COLOSSUS` = `7.0`
- `FIGHT_TYPE_FARMER` = `1.0`
- `FIGHT_TYPE_SOLO` = `0.0`
- `FIGHT_TYPE_TEAM` = `2.0`
- `FIGHT_TYPE_WAR` = `5.0`
- `INSTRUCTIONS_LIMIT` = `300000.0`
- `Infinity` = `Infinity`
- `LAUNCH_TYPE_CIRCLE` = `7.0`
- `LAUNCH_TYPE_DIAGONAL` = `2.0`
- `LAUNCH_TYPE_DIAGONAL_INVERTED` = `5.0`
- `LAUNCH_TYPE_LINE` = `1.0`
- `LAUNCH_TYPE_LINE_INVERTED` = `6.0`
- `LAUNCH_TYPE_STAR` = `3.0`
- `LAUNCH_TYPE_STAR_INVERTED` = `4.0`
- `MAP_BEACH` = `6.0`
- `MAP_CASTLE` = `9.0`
- `MAP_CEMETERY` = `10.0`
- `MAP_DESERT` = `3.0`
- `MAP_FACTORY` = `2.0`
- `MAP_FOREST` = `4.0`
- `MAP_GLACIER` = `5.0`
- `MAP_NEXUS` = `1.0`
- `MAP_TEIEN` = `8.0`
- `MAP_TEMPLE` = `7.0`
- `MAX_TURNS` = `64.0`
- `MESSAGE_ATTACK` = `2.0`
- `MESSAGE_BUFF_AGILITY` = `8.0`
- `MESSAGE_BUFF_FORCE` = `7.0`
- `MESSAGE_BUFF_MP` = `5.0`
- `MESSAGE_BUFF_STRENGTH` = `7.0`
- `MESSAGE_BUFF_TP` = `6.0`
- `MESSAGE_CUSTOM` = `13.0`
- `MESSAGE_DEBUFF` = `3.0`
- `MESSAGE_HEAL` = `1.0`
- `MESSAGE_MOVE_AWAY` = `10.0`
- `MESSAGE_MOVE_AWAY_CELL` = `12.0`
- `MESSAGE_MOVE_TOWARD` = `9.0`
- `MESSAGE_MOVE_TOWARD_CELL` = `11.0`
- `MESSAGE_SHIELD` = `4.0`
- `MOB_BLUE_CRYSTAL` = `7.0`
- `MOB_EVIL_PUMPKIN` = `3.0`
- `MOB_FENNEL_KING` = `2.0`
- `MOB_FENNEL_KNIGHT` = `16.0`
- `MOB_FENNEL_SCRIBE` = `18.0`
- `MOB_FENNEL_SQUIRE` = `17.0`
- `MOB_GRAAL` = `4.0`
- `MOB_GREEN_CRYSTAL` = `6.0`
- `MOB_HUBBARD` = `11.0`
- `MOB_NASU_RONIN` = `15.0`
- `MOB_NASU_SAMURAI` = `1.0`
- `MOB_NASU_SEITO` = `13.0`
- `MOB_NASU_WARRIOR` = `14.0`
- `MOB_OFFSPRING` = `12.0`
- `MOB_RED_CRYSTAL` = `5.0`
- `MOB_TURBAN` = `9.0`
- `MOB_WARTY` = `10.0`
- `MOB_YELLOW_CRYSTAL` = `8.0`
- `NaN` = `NaN`
- `OPERATIONS_LIMIT` = `2.0E7`
- `PI` = `3.141592653589793`
- `PLANT_CHILLI_PEPPER` = `10.0`
- `PLANT_CORN` = `9.0`
- `PLANT_PROTOTAXITE` = `13.0`
- `SORT_ASC` = `0.0`
- `SORT_DESC` = `1.0`
- `STATE_INVINCIBLE` = `3.0`
- `STATE_PACIFIST` = `4.0`
- `STATE_ROOTED` = `9.0`
- `STATE_STATIC` = `11.0`
- `STATE_STERILE` = `12.0`
- `STATE_UNHEALABLE` = `2.0`
- `STAT_ABSOLUTE_SHIELD` = `9.0`
- `STAT_AGILITY` = `4.0`
- `STAT_CORES` = `16.0`
- `STAT_DAMAGE_RETURN` = `14.0`
- `STAT_FREQUENCY` = `5.0`
- `STAT_LIFE` = `0.0`
- `STAT_MAGIC` = `13.0`
- `STAT_MP` = `2.0`
- `STAT_POWER` = `15.0`
- `STAT_RAM` = `17.0`
- `STAT_RELATIVE_SHIELD` = `10.0`
- `STAT_RESISTANCE` = `11.0`
- `STAT_SCIENCE` = `12.0`
- `STAT_STRENGTH` = `3.0`
- `STAT_TP` = `1.0`
- `STAT_WISDOM` = `6.0`
- `SUMMON_LIMIT` = `8.0`
- `TYPE_ARRAY` = `4.0`
- `TYPE_BOOLEAN` = `2.0`
- `TYPE_CLASS` = `6.0`
- `TYPE_FUNCTION` = `5.0`
- `TYPE_INTERVAL` = `10.0`
- `TYPE_MAP` = `8.0`
- `TYPE_NULL` = `0.0`
- `TYPE_NUMBER` = `1.0`
- `TYPE_OBJECT` = `7.0`
- `TYPE_SET` = `9.0`
- `TYPE_STRING` = `3.0`
- `USE_CRITICAL` = `2.0`
- `USE_FAILED` = `0.0`
- `USE_INVALID_COOLDOWN` = `-3.0`
- `USE_INVALID_POSITION` = `-4.0`
- `USE_INVALID_TARGET` = `-1.0`
- `USE_MAX_USES` = `-7.0`
- `USE_NOT_ENOUGH_TP` = `-2.0`
- `USE_RESURRECT_INVALID_ENTITY` = `-6.0`
- `USE_SUCCESS` = `1.0`
- `USE_TOO_MANY_SUMMONS` = `-5.0`
- `USE_TOO_MUCH_SUMMONS` = `-5.0`
- `WEAPON_AXE` = `109.0`
- `WEAPON_BAZOOKA` = `184.0`
- `WEAPON_BROADSWORD` = `108.0`
- `WEAPON_B_LASER` = `60.0`
- `WEAPON_DARK_KATANA` = `187.0`
- `WEAPON_DESERT_SABER` = `429.0`
- `WEAPON_DESTROYER` = `40.0`
- `WEAPON_DOUBLE_GUN` = `39.0`
- `WEAPON_ELECTRISOR` = `44.0`
- `WEAPON_ENHANCED_LIGHTNINGER` = `225.0`
- `WEAPON_EXCALIBUR` = `409.0`
- `WEAPON_EXPLORER_RIFLE` = `175.0`
- `WEAPON_FLAME_THROWER` = `46.0`
- `WEAPON_GAZOR` = `48.0`
- `WEAPON_GRENADE_LAUNCHER` = `43.0`
- `WEAPON_HEAVY_SWORD` = `278.0`
- `WEAPON_ILLICIT_GRENADE_LAUNCHER` = `116.0`
- `WEAPON_J_LASER` = `115.0`
- `WEAPON_KATANA` = `107.0`
- `WEAPON_LASER` = `42.0`
- `WEAPON_LIGHTNINGER` = `180.0`
- `WEAPON_MACHINE_GUN` = `38.0`
- `WEAPON_MAGNUM` = `45.0`
- `WEAPON_MYSTERIOUS_ELECTRISOR` = `117.0`
- `WEAPON_M_LASER` = `47.0`
- `WEAPON_NEUTRINO` = `182.0`
- `WEAPON_ODACHI` = `408.0`
- `WEAPON_PISTOL` = `37.0`
- `WEAPON_PLUTONIUM_BAZOOKA` = `506.0`
- `WEAPON_QUANTUM_RIFLE` = `428.0`
- `WEAPON_REVOKED_M_LASER` = `119.0`
- `WEAPON_RHINO` = `153.0`
- `WEAPON_RIFLE` = `151.0`
- `WEAPON_SCYTHE` = `410.0`
- `WEAPON_SHOTGUN` = `41.0`
- `WEAPON_SUN_SPEAR` = `440.0`
- `WEAPON_SWORD` = `277.0`
- `WEAPON_UNBRIDLED_GAZOR` = `118.0`
- `WEAPON_UNSTABLE_DESTROYER` = `226.0`
