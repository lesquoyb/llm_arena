# LeekScript 4 API reference

Engine: `b99a174dd938260d9e47b2e65a208cb32230e26e`.

Signatures extracted from the compiled engine. Arguments are positional; names and behavior are not included.
Costs are declared base costs. Zero does not mean free; some costs are calculated elsewhere.

## Functions

### abs

Namespace: Number. Declared base cost: 1 operations.

- `abs[real] => real`
- `abs[integer] => integer`
- `abs[big_integer] => big_integer`

### acos

Namespace: Number. Declared base cost: 3 operations.

- `acos[real] => real`

### arrayChunk

Namespace: Array. Declared base cost: 0 operations.

- `arrayChunk[Array, integer] => Array`

### arrayClear

Namespace: Array. Declared base cost: 1 operations.

- `arrayClear[Array] => Array`

### arrayConcat

Namespace: Array. Declared base cost: 0 operations.

- `arrayConcat[Array, Array] => Array`

### arrayEvery

Namespace: Array. Declared base cost: 0 operations.

- `arrayEvery[Array, Function<any, integer, Array => boolean>] => boolean`

### arrayFilter

Namespace: Array. Declared base cost: 0 operations.

- `arrayFilter[Array, Function<any, integer, Array => boolean>] => Array`

### arrayFind

Namespace: Array. Declared base cost: 0 operations.

- `arrayFind[Array, Function<any, integer, Array => boolean>] => any`

### arrayFlatten

Namespace: Array. Declared base cost: 0 operations.

- `arrayFlatten[Array, integer] => Array`
- `arrayFlatten[Array] => Array`

### arrayFoldLeft

Namespace: Array. Declared base cost: 0 operations.

- `arrayFoldLeft[Array, Function<any, any, integer, Array => any>, any] => any`

### arrayFoldRight

Namespace: Array. Declared base cost: 0 operations.

- `arrayFoldRight[Array, Function<any, any, integer, Array => any>, any] => any`

### arrayFrequencies

Namespace: Array. Declared base cost: 0 operations.

- `arrayFrequencies[Array] => Map`

### arrayGet

Namespace: Array. Declared base cost: 1 operations.

- `arrayGet[Array, integer, any] => any`
- `arrayGet[Array, integer] => any`

### arrayIter

Namespace: Array. Declared base cost: 0 operations.

- `arrayIter[Array, Function<any, integer, Array => any>] => void`

### arrayMap

Namespace: Array. Declared base cost: 0 operations.

- `arrayMap[Array, Function<any, integer, Array => any>] => Array`

### arrayMax

Namespace: Array. Declared base cost: 0 operations.

- `arrayMax[Array] => any`

### arrayMin

Namespace: Array. Declared base cost: 0 operations.

- `arrayMin[Array] => any`

### arrayPartition

Namespace: Array. Declared base cost: 0 operations.

- `arrayPartition[Array, Function<any, integer, Array => boolean>] => Array`

### arrayRandom

Namespace: Array. Declared base cost: 0 operations.

- `arrayRandom[Array, integer] => Array`
- `arrayRandom[Array] => Array`

### arrayRemoveAll

Namespace: Array. Declared base cost: 0 operations.

- `arrayRemoveAll[Array, any] => void`

### arraySlice

Namespace: Array. Declared base cost: 0 operations.

- `arraySlice[Array, any, any, integer] => Array`
- `arraySlice[Array, any, any] => Array`
- `arraySlice[Array, any] => Array`

### arraySome

Namespace: Array. Declared base cost: 0 operations.

- `arraySome[Array, Function<any, integer, Array => boolean>] => boolean`

### arraySort

Namespace: Array. Declared base cost: 0 operations.

- `arraySort[Array, Function<any, any => real | integer>] => Array`
- `arraySort[Array] => Array`

### arrayToSet

Namespace: Array. Declared base cost: 0 operations.

- `arrayToSet[Array] => Set`

### arrayUnique

Namespace: Array. Declared base cost: 0 operations.

- `arrayUnique[Array] => Array`

### asin

Namespace: Number. Declared base cost: 3 operations.

- `asin[real] => real`

### atan

Namespace: Number. Declared base cost: 3 operations.

- `atan[real] => real`

### atan2

Namespace: Number. Declared base cost: 4 operations.

- `atan2[real, real] => real`

### average

Namespace: Array. Declared base cost: 0 operations.

- `average[Array] => real`

### binString

Namespace: Number. Declared base cost: 9 operations.

- `binString[integer] => string`
- `binString[big_integer] => string`

### bitCount

Namespace: Number. Declared base cost: 1 operations.

- `bitCount[integer] => integer`
- `bitCount[big_integer] => integer`

### bitLength

Namespace: Number. Declared base cost: 1 operations.

- `bitLength[integer] => integer`
- `bitLength[big_integer] => integer`

### bitReverse

Namespace: Number. Declared base cost: 1 operations.

- `bitReverse[integer] => integer`

### bitsToReal

Namespace: Number. Declared base cost: 3 operations.

- `bitsToReal[integer] => real`

### byteReverse

Namespace: Number. Declared base cost: 1 operations.

- `byteReverse[integer] => integer`

### canUseChip

Namespace: Chip. Declared base cost: 45 operations.

- `canUseChip[integer, integer] => boolean`

### canUseChipOnCell

Namespace: Chip. Declared base cost: 45 operations.

- `canUseChipOnCell[integer, integer] => boolean`

### canUseWeapon

Namespace: Weapon. Declared base cost: 45 operations.

- `canUseWeapon[integer?, integer?] => boolean`
- `canUseWeapon[integer?] => boolean`

### canUseWeaponOnCell

Namespace: Weapon. Declared base cost: 45 operations.

- `canUseWeaponOnCell[integer?, integer?] => boolean`
- `canUseWeaponOnCell[integer?] => boolean`

### cbrt

Namespace: Number. Declared base cost: 5 operations.

- `cbrt[real] => real`

### ceil

Namespace: Number. Declared base cost: 1 operations.

- `ceil[real] => integer`
- `ceil[integer] => integer`

### charAt

Namespace: String. Declared base cost: 4 operations.

- `charAt[string, integer] => string`

### chipNeedLos

Namespace: Chip. Declared base cost: 10 operations.

- `chipNeedLos[integer] => boolean`

### clearMarks

Namespace: Util. Declared base cost: 15 operations.

- `clearMarks[] => void`

### clone

Namespace: Value. Declared base cost: 0 operations.

- `clone[any, integer] => any`
- `clone[any] => any`

### codePointAt

Namespace: String. Declared base cost: 1 operations.

- `codePointAt[string, integer] => integer`
- `codePointAt[string] => integer`

### contains

Namespace: String. Declared base cost: 0 operations.

- `contains[string, string] => boolean`

### cos

Namespace: Number. Declared base cost: 3 operations.

- `cos[real] => real`

### count

Namespace: Array. Declared base cost: 1 operations.

- `count[Array] => integer`

### debug

Namespace: System. Declared base cost: 100 operations.

- `debug[any] => void`

### debugC

Namespace: System. Declared base cost: 100 operations.

- `debugC[any, integer] => void`

### debugE

Namespace: System. Declared base cost: 100 operations.

- `debugE[any] => void`

### debugW

Namespace: System. Declared base cost: 100 operations.

- `debugW[any] => void`

### deleteRegister

Namespace: Util. Declared base cost: 16 operations.

- `deleteRegister[string] => void`

### endsWith

Namespace: String. Declared base cost: 0 operations.

- `endsWith[string, string] => boolean`

### exp

Namespace: Number. Declared base cost: 2 operations.

- `exp[real] => real`

### fill

Namespace: Array. Declared base cost: 0 operations.

- `fill[Array, any, integer] => void`
- `fill[Array, any] => void`

### floor

Namespace: Number. Declared base cost: 1 operations.

- `floor[real] => integer`
- `floor[integer] => integer`

### getAIID

Namespace: Entity. Declared base cost: 15 operations.

- `getAIID[integer?] => integer?`
- `getAIID[] => integer`

### getAIName

Namespace: Entity. Declared base cost: 15 operations.

- `getAIName[integer?] => string?`
- `getAIName[] => string`

### getAbsoluteShield

Namespace: Entity. Declared base cost: 15 operations.

- `getAbsoluteShield[integer?] => integer?`
- `getAbsoluteShield[] => integer`

### getAgility

Namespace: Entity. Declared base cost: 15 operations.

- `getAgility[integer?] => integer?`
- `getAgility[] => integer`

### getAliveAllies

Namespace: Fight. Declared base cost: 100 operations.

- `getAliveAllies[] => Array<integer>`

### getAliveAlliesCount

Namespace: Fight. Declared base cost: 100 operations.

- `getAliveAlliesCount[] => integer`

### getAliveEnemies

Namespace: Fight. Declared base cost: 100 operations.

- `getAliveEnemies[] => Array<integer>`

### getAliveEnemiesCount

Namespace: Fight. Declared base cost: 25 operations.

- `getAliveEnemiesCount[] => integer`

### getAllChips

Namespace: Chip. Declared base cost: 200 operations.

- `getAllChips[] => Array<integer>`

### getAllEffects

Namespace: Fight. Declared base cost: 200 operations.

- `getAllEffects[] => Array<integer>`

### getAllWeapons

Namespace: Weapon. Declared base cost: 200 operations.

- `getAllWeapons[] => Array<integer>`

### getAlliedTurret

Namespace: Fight. Declared base cost: 15 operations.

- `getAlliedTurret[] => integer?`

### getAllies

Namespace: Fight. Declared base cost: 100 operations.

- `getAllies[] => Array<integer>`

### getAlliesCount

Namespace: Fight. Declared base cost: 25 operations.

- `getAlliesCount[] => integer`

### getAlliesLife

Namespace: Fight. Declared base cost: 50 operations.

- `getAlliesLife[] => integer`

### getAwakeningZone

Namespace: Entity. Declared base cost: 15 operations.

- `getAwakeningZone[integer?] => integer?`
- `getAwakeningZone[] => integer`

### getBirthTurn

Namespace: Entity. Declared base cost: 15 operations.

- `getBirthTurn[integer?] => integer?`
- `getBirthTurn[] => integer`

### getBlue

Namespace: Color. Declared base cost: 1 operations.

- `getBlue[integer] => integer`

### getBulbCharacteristics

Namespace: Fight. Declared base cost: 40 operations.

- `getBulbCharacteristics[integer] => Map`

### getBulbChips

Namespace: Fight. Declared base cost: 40 operations.

- `getBulbChips[integer] => Array?`

### getBulbStats

Namespace: Fight. Declared base cost: 40 operations.

- `getBulbStats[integer] => Map`

### getBulbType

Namespace: Entity. Declared base cost: 15 operations.

- `getBulbType[integer?] => integer?`
- `getBulbType[] => integer`

### getCell

Namespace: Entity. Declared base cost: 5 operations.

- `getCell[integer?] => integer?`
- `getCell[] => integer?`

### getCellContent

Namespace: Field. Declared base cost: 6 operations.

- `getCellContent[integer] => integer`

### getCellDistance

Namespace: Field. Declared base cost: 15 operations.

- `getCellDistance[integer, integer] => integer`

### getCellFromXY

Namespace: Field. Declared base cost: 5 operations.

- `getCellFromXY[integer, integer] => integer?`

### getCellToUseChip

Namespace: Fight. Declared base cost: 38080 operations.

- `getCellToUseChip[integer, integer?, Array<integer>?] => integer`
- `getCellToUseChip[integer, integer?] => integer`

### getCellToUseChipOnCell

Namespace: Fight. Declared base cost: 38080 operations.

- `getCellToUseChipOnCell[integer, integer?, Array<integer>?] => integer`
- `getCellToUseChipOnCell[integer, integer?] => integer`

### getCellToUseWeapon

Namespace: Fight. Declared base cost: 38080 operations.

- `getCellToUseWeapon[integer, integer?, Array<integer>?] => integer`
- `getCellToUseWeapon[integer, integer?] => integer`
- `getCellToUseWeapon[integer] => integer`

### getCellToUseWeaponOnCell

Namespace: Fight. Declared base cost: 38080 operations.

- `getCellToUseWeaponOnCell[integer, integer?, Array<integer>?] => integer`
- `getCellToUseWeaponOnCell[integer, integer?] => integer`
- `getCellToUseWeaponOnCell[integer] => integer`

### getCellX

Namespace: Field. Declared base cost: 5 operations.

- `getCellX[integer] => integer?`

### getCellY

Namespace: Field. Declared base cost: 5 operations.

- `getCellY[integer] => integer?`

### getCellsToUseChip

Namespace: Fight. Declared base cost: 25834 operations.

- `getCellsToUseChip[integer, integer, Array<integer>?] => Array<integer>?`
- `getCellsToUseChip[integer, integer] => Array<integer>?`

### getCellsToUseChipOnCell

Namespace: Fight. Declared base cost: 25834 operations.

- `getCellsToUseChipOnCell[integer, integer, Array<integer>?] => Array<integer>?`
- `getCellsToUseChipOnCell[integer, integer] => Array<integer>?`

### getCellsToUseWeapon

Namespace: Fight. Declared base cost: 25834 operations.

- `getCellsToUseWeapon[integer, integer?, Array<integer>?] => Array<integer>?`
- `getCellsToUseWeapon[integer, integer?] => Array<integer>?`
- `getCellsToUseWeapon[integer] => Array<integer>?`

### getCellsToUseWeaponOnCell

Namespace: Fight. Declared base cost: 25834 operations.

- `getCellsToUseWeaponOnCell[integer, integer, Array<integer>?] => Array<integer>?`
- `getCellsToUseWeaponOnCell[integer, integer] => Array<integer>?`
- `getCellsToUseWeaponOnCell[integer] => Array<integer>?`

### getChestType

Namespace: Entity. Declared base cost: 15 operations.

- `getChestType[integer?] => integer?`
- `getChestType[] => integer`

### getChipArea

Namespace: Chip. Declared base cost: 15 operations.

- `getChipArea[integer] => integer?`

### getChipCooldown

Namespace: Chip. Declared base cost: 15 operations.

- `getChipCooldown[integer] => integer`

### getChipCost

Namespace: Chip. Declared base cost: 15 operations.

- `getChipCost[integer] => integer?`

### getChipEffectiveArea

Namespace: Chip. Declared base cost: 78 operations.

- `getChipEffectiveArea[integer, integer, integer?] => Array<integer>?`
- `getChipEffectiveArea[integer, integer] => Array<integer>?`

### getChipEffects

Namespace: Chip. Declared base cost: 125 operations.

- `getChipEffects[integer] => Array<Array<real | integer>>?`

### getChipFailure

Namespace: Chip. Declared base cost: 15 operations.

- `getChipFailure[integer] => integer`

### getChipLaunchType

Namespace: Chip. Declared base cost: 15 operations.

- `getChipLaunchType[integer] => integer?`

### getChipMaxRange

Namespace: Chip. Declared base cost: 15 operations.

- `getChipMaxRange[integer] => integer?`

### getChipMaxScope

Namespace: Chip. Declared base cost: 15 operations.

- `getChipMaxScope[integer] => integer?`

### getChipMaxUses

Namespace: Chip. Declared base cost: 15 operations.

- `getChipMaxUses[integer] => integer?`

### getChipMinRange

Namespace: Chip. Declared base cost: 15 operations.

- `getChipMinRange[integer] => integer?`

### getChipMinScope

Namespace: Chip. Declared base cost: 15 operations.

- `getChipMinScope[integer] => integer?`

### getChipName

Namespace: Chip. Declared base cost: 15 operations.

- `getChipName[integer] => string`

### getChipTargets

Namespace: Chip. Declared base cost: 40 operations.

- `getChipTargets[integer, integer] => Array<integer>?`

### getChips

Namespace: Entity. Declared base cost: 40 operations.

- `getChips[integer?] => Array<integer>?`
- `getChips[] => Array<integer>`

### getColor

Namespace: Color. Declared base cost: 7 operations.

- `getColor[integer, integer, integer] => integer`

### getCompositionName

Namespace: Entity. Declared base cost: 15 operations.

- `getCompositionName[integer?] => string?`
- `getCompositionName[] => string`

### getCooldown

Namespace: Chip. Declared base cost: 30 operations.

- `getCooldown[integer, integer?] => integer?`
- `getCooldown[integer] => integer`

### getCores

Namespace: Entity. Declared base cost: 15 operations.

- `getCores[integer?] => integer?`
- `getCores[] => integer`

### getDamageReturn

Namespace: Entity. Declared base cost: 15 operations.

- `getDamageReturn[integer?] => integer?`
- `getDamageReturn[] => integer`

### getDate

Namespace: System. Declared base cost: 50 operations.

- `getDate[] => string`

### getDeadAllies

Namespace: Fight. Declared base cost: 100 operations.

- `getDeadAllies[] => Array<integer>`

### getDeadEnemies

Namespace: Fight. Declared base cost: 100 operations.

- `getDeadEnemies[] => Array<integer>`

### getDeadEnemiesCount

Namespace: Fight. Declared base cost: 25 operations.

- `getDeadEnemiesCount[] => integer`

### getDistance

Namespace: Field. Declared base cost: 15 operations.

- `getDistance[integer, integer] => real`

### getEffects

Namespace: Entity. Declared base cost: 25 operations.

- `getEffects[integer?] => Array<Array<boolean | integer>>?`
- `getEffects[] => Array<Array<boolean | integer>>`

### getEnemies

Namespace: Fight. Declared base cost: 100 operations.

- `getEnemies[] => Array<integer>`

### getEnemiesCount

Namespace: Fight. Declared base cost: 25 operations.

- `getEnemiesCount[] => integer`

### getEnemiesLife

Namespace: Fight. Declared base cost: 50 operations.

- `getEnemiesLife[] => integer`

### getEnemyTurret

Namespace: Fight. Declared base cost: 15 operations.

- `getEnemyTurret[] => integer?`

### getEntity

Namespace: Entity. Declared base cost: 5 operations.

- `getEntity[] => integer`

### getEntityOnCell

Namespace: Field. Declared base cost: 15 operations.

- `getEntityOnCell[integer] => integer`

### getEntityTurnOrder

Namespace: Entity. Declared base cost: 30 operations.

- `getEntityTurnOrder[integer?] => integer?`
- `getEntityTurnOrder[] => integer`

### getFarmerCountry

Namespace: Entity. Declared base cost: 15 operations.

- `getFarmerCountry[integer?] => string?`
- `getFarmerCountry[] => string`

### getFarmerID

Namespace: Entity. Declared base cost: 15 operations.

- `getFarmerID[integer?] => integer?`
- `getFarmerID[] => integer`

### getFarmerName

Namespace: Entity. Declared base cost: 15 operations.

- `getFarmerName[integer?] => string?`
- `getFarmerName[] => string`

### getFarthestAlly

Namespace: Fight. Declared base cost: 31 operations.

- `getFarthestAlly[] => integer`

### getFarthestEnemy

Namespace: Fight. Declared base cost: 31 operations.

- `getFarthestEnemy[] => integer`

### getFightBoss

Namespace: Fight. Declared base cost: 10 operations.

- `getFightBoss[] => integer`

### getFightContext

Namespace: Fight. Declared base cost: 10 operations.

- `getFightContext[] => integer`

### getFightID

Namespace: Fight. Declared base cost: 5 operations.

- `getFightID[] => integer`

### getFightType

Namespace: Fight. Declared base cost: 10 operations.

- `getFightType[] => integer`

### getForce

Namespace: Entity. Declared base cost: 15 operations.

- `getForce[integer?] => integer?`
- `getForce[] => integer`

### getFrequency

Namespace: Entity. Declared base cost: 15 operations.

- `getFrequency[integer?] => integer?`
- `getFrequency[] => integer`

### getGreen

Namespace: Color. Declared base cost: 2 operations.

- `getGreen[integer] => integer`

### getInstructionsCount

Namespace: System. Declared base cost: 1 operations.

- `getInstructionsCount[] => integer`

### getItemUses

Namespace: Entity. Declared base cost: 15 operations.

- `getItemUses[integer] => integer`

### getLaunchedEffects

Namespace: Entity. Declared base cost: 25 operations.

- `getLaunchedEffects[integer?] => Array<Array<boolean | integer>>?`
- `getLaunchedEffects[] => Array<Array<boolean | integer>>`

### getLeekID

Namespace: Entity. Declared base cost: 15 operations.

- `getLeekID[integer?] => integer?`
- `getLeekID[] => integer`

### getLevel

Namespace: Entity. Declared base cost: 15 operations.

- `getLevel[integer?] => integer?`
- `getLevel[] => integer`

### getLife

Namespace: Entity. Declared base cost: 15 operations.

- `getLife[integer?] => integer?`
- `getLife[] => integer`

### getMP

Namespace: Entity. Declared base cost: 15 operations.

- `getMP[integer?] => integer?`
- `getMP[] => integer`

### getMagic

Namespace: Entity. Declared base cost: 15 operations.

- `getMagic[integer?] => integer?`
- `getMagic[] => integer`

### getMapType

Namespace: Field. Declared base cost: 5 operations.

- `getMapType[] => integer`

### getMaxOperations

Namespace: System. Declared base cost: 1 operations.

- `getMaxOperations[] => integer`

### getMaxRAM

Namespace: System. Declared base cost: 1 operations.

- `getMaxRAM[] => integer`

### getMessageAuthor

Namespace: Network. Declared base cost: 5 operations.

- `getMessageAuthor[Array] => integer`

### getMessageParams

Namespace: Network. Declared base cost: 5 operations.

- `getMessageParams[Array] => any`

### getMessageType

Namespace: Network. Declared base cost: 5 operations.

- `getMessageType[Array] => integer`

### getMessages

Namespace: Network. Declared base cost: 0 operations.

- `getMessages[integer] => Array<Array>`
- `getMessages[] => Array<Array>`

### getMobType

Namespace: Entity. Declared base cost: 15 operations.

- `getMobType[integer?] => integer?`
- `getMobType[] => integer`

### getName

Namespace: Entity. Declared base cost: 15 operations.

- `getName[integer?] => string?`
- `getName[] => string`

### getNearestAlly

Namespace: Fight. Declared base cost: 25 operations.

- `getNearestAlly[] => integer`

### getNearestAllyTo

Namespace: Fight. Declared base cost: 35 operations.

- `getNearestAllyTo[integer] => integer?`

### getNearestAllyToCell

Namespace: Fight. Declared base cost: 35 operations.

- `getNearestAllyToCell[integer] => integer?`

### getNearestEnemy

Namespace: Fight. Declared base cost: 25 operations.

- `getNearestEnemy[] => integer`

### getNearestEnemyTo

Namespace: Fight. Declared base cost: 35 operations.

- `getNearestEnemyTo[integer] => integer?`

### getNearestEnemyToCell

Namespace: Fight. Declared base cost: 35 operations.

- `getNearestEnemyToCell[integer] => integer?`

### getNextPlayer

Namespace: Fight. Declared base cost: 20 operations.

- `getNextPlayer[integer?] => integer?`
- `getNextPlayer[] => integer`

### getObstacles

Namespace: Field. Declared base cost: 85 operations.

- `getObstacles[] => Array<integer>`

### getOperations

Namespace: System. Declared base cost: 1 operations.

- `getOperations[] => integer`

### getPassiveEffects

Namespace: Entity. Declared base cost: 125 operations.

- `getPassiveEffects[integer?] => Array<Array<real | integer>>?`
- `getPassiveEffects[] => Array<Array<real | integer>>`

### getPath

Namespace: Field. Declared base cost: 0 operations.

- `getPath[integer, integer, Array?] => Array<integer>?`
- `getPath[integer, integer] => Array<integer>?`

### getPathLength

Namespace: Field. Declared base cost: 0 operations.

- `getPathLength[integer, integer, Array?] => integer?`
- `getPathLength[integer, integer] => integer?`

### getPlantTrigger

Namespace: Entity. Declared base cost: 15 operations.

- `getPlantTrigger[] => integer`

### getPlantType

Namespace: Entity. Declared base cost: 15 operations.

- `getPlantType[integer?] => integer?`
- `getPlantType[] => integer`

### getPower

Namespace: Entity. Declared base cost: 15 operations.

- `getPower[integer?] => integer?`
- `getPower[] => integer`

### getPreviousPlayer

Namespace: Fight. Declared base cost: 20 operations.

- `getPreviousPlayer[integer?] => integer?`
- `getPreviousPlayer[] => integer`

### getRAM

Namespace: Entity. Declared base cost: 15 operations.

- `getRAM[integer?] => integer?`
- `getRAM[] => integer`

### getRed

Namespace: Color. Declared base cost: 2 operations.

- `getRed[integer] => integer`

### getRegister

Namespace: Util. Declared base cost: 15 operations.

- `getRegister[string] => string?`

### getRegisters

Namespace: Util. Declared base cost: 25 operations.

- `getRegisters[] => Map<string, string>`

### getRelativeShield

Namespace: Entity. Declared base cost: 15 operations.

- `getRelativeShield[integer?] => integer?`
- `getRelativeShield[] => integer`

### getResistance

Namespace: Entity. Declared base cost: 15 operations.

- `getResistance[integer?] => integer?`
- `getResistance[] => integer`

### getScience

Namespace: Entity. Declared base cost: 15 operations.

- `getScience[integer?] => integer?`
- `getScience[] => integer`

### getSide

Namespace: Entity. Declared base cost: 5 operations.

- `getSide[integer?] => integer?`
- `getSide[] => integer`

### getStat

Namespace: Entity. Declared base cost: 15 operations.

- `getStat[integer?, integer] => integer?`
- `getStat[integer] => integer`

### getStates

Namespace: Entity. Declared base cost: 25 operations.

- `getStates[integer] => Set<integer>?`
- `getStates[] => Set<integer>`

### getStats

Namespace: Entity. Declared base cost: 40 operations.

- `getStats[integer?] => Map<integer, integer>?`
- `getStats[] => Map<integer, integer>`

### getStrength

Namespace: Entity. Declared base cost: 15 operations.

- `getStrength[integer?] => integer?`
- `getStrength[] => integer`

### getSummoner

Namespace: Entity. Declared base cost: 15 operations.

- `getSummoner[integer?] => integer?`
- `getSummoner[] => integer`

### getSummons

Namespace: Entity. Declared base cost: 15 operations.

- `getSummons[integer?] => Array<integer>`
- `getSummons[] => Array<integer>`

### getTP

Namespace: Entity. Declared base cost: 15 operations.

- `getTP[integer?] => integer?`
- `getTP[] => integer`

### getTeamID

Namespace: Entity. Declared base cost: 15 operations.

- `getTeamID[integer?] => integer?`
- `getTeamID[] => integer`

### getTeamName

Namespace: Entity. Declared base cost: 15 operations.

- `getTeamName[integer?] => string?`
- `getTeamName[] => string`

### getTime

Namespace: System. Declared base cost: 50 operations.

- `getTime[] => string`

### getTimestamp

Namespace: System. Declared base cost: 5 operations.

- `getTimestamp[] => integer`

### getTotalLife

Namespace: Entity. Declared base cost: 15 operations.

- `getTotalLife[integer?] => integer?`
- `getTotalLife[] => integer`

### getTotalMP

Namespace: Entity. Declared base cost: 15 operations.

- `getTotalMP[integer?] => integer?`
- `getTotalMP[] => integer`

### getTotalTP

Namespace: Entity. Declared base cost: 15 operations.

- `getTotalTP[integer?] => integer?`
- `getTotalTP[] => integer`

### getTurn

Namespace: Fight. Declared base cost: 15 operations.

- `getTurn[] => integer`

### getType

Namespace: Entity. Declared base cost: 15 operations.

- `getType[integer?] => integer?`
- `getType[] => integer`

### getUsedRAM

Namespace: System. Declared base cost: 1 operations.

- `getUsedRAM[] => integer`

### getWeapon

Namespace: Entity. Declared base cost: 15 operations.

- `getWeapon[integer?] => integer?`
- `getWeapon[] => integer?`

### getWeaponArea

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponArea[integer] => integer?`

### getWeaponCost

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponCost[integer] => integer`
- `getWeaponCost[] => integer`

### getWeaponEffectiveArea

Namespace: Weapon. Declared base cost: 78 operations.

- `getWeaponEffectiveArea[integer, integer?, integer?] => Array<integer>?`
- `getWeaponEffectiveArea[integer, integer?] => Array<integer>?`
- `getWeaponEffectiveArea[integer] => Array<integer>?`

### getWeaponEffects

Namespace: Weapon. Declared base cost: 125 operations.

- `getWeaponEffects[integer] => Array<Array<real | integer>>?`
- `getWeaponEffects[] => Array<Array<real | integer>>?`

### getWeaponFailure

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponFailure[integer] => integer`
- `getWeaponFailure[] => integer`

### getWeaponLaunchType

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponLaunchType[integer] => integer?`
- `getWeaponLaunchType[] => integer?`

### getWeaponMaxRange

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponMaxRange[integer] => integer`
- `getWeaponMaxRange[] => integer`

### getWeaponMaxUses

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponMaxUses[integer] => integer`
- `getWeaponMaxUses[] => integer`

### getWeaponMinRange

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponMinRange[integer] => integer`
- `getWeaponMinRange[] => integer`

### getWeaponName

Namespace: Weapon. Declared base cost: 15 operations.

- `getWeaponName[integer] => string`
- `getWeaponName[] => string`

### getWeaponPassiveEffects

Namespace: Weapon. Declared base cost: 125 operations.

- `getWeaponPassiveEffects[integer] => Array<Array<real | integer>>`
- `getWeaponPassiveEffects[] => Array<Array<real | integer>>`

### getWeaponTargets

Namespace: Weapon. Declared base cost: 40 operations.

- `getWeaponTargets[integer, integer?] => Array<integer>?`
- `getWeaponTargets[integer] => Array<integer>?`

### getWeapons

Namespace: Entity. Declared base cost: 50 operations.

- `getWeapons[integer?] => Array<integer>?`
- `getWeapons[] => Array<integer>`

### getWinner

Namespace: Fight. Declared base cost: 5 operations.

- `getWinner[] => integer`

### getWisdom

Namespace: Entity. Declared base cost: 15 operations.

- `getWisdom[integer?] => integer?`
- `getWisdom[] => integer`

### hexString

Namespace: Number. Declared base cost: 6 operations.

- `hexString[integer] => string`
- `hexString[big_integer] => string`

### hypot

Namespace: Number. Declared base cost: 2 operations.

- `hypot[real, real] => real`

### inArray

Namespace: Array. Declared base cost: 0 operations.

- `inArray[Array, any] => boolean`

### indexOf

Namespace: String. Declared base cost: 0 operations.

- `indexOf[string, string, integer] => integer`
- `indexOf[string, string] => integer`

### insert

Namespace: Array. Declared base cost: 0 operations.

- `insert[Array, any, integer] => void`

### intervalAverage

Namespace: Interval. Declared base cost: 3 operations.

- `intervalAverage[Interval] => real`

### intervalCombine

Namespace: Interval. Declared base cost: 3 operations.

- `intervalCombine[Interval<real>, Interval<real>] => Interval<real>`
- `intervalCombine[Interval<integer>, Interval<real>] => Interval<real>`
- `intervalCombine[Interval<real>, Interval<integer>] => Interval<real>`
- `intervalCombine[Interval<integer>, Interval<integer>] => Interval<integer>`

### intervalContains

Namespace: Interval. Declared base cost: 2 operations.

- `intervalContains[Interval, integer] => boolean`
- `intervalContains[Interval, real] => boolean`
- `intervalContains[Interval, real | integer] => boolean`

### intervalIntersection

Namespace: Interval. Declared base cost: 3 operations.

- `intervalIntersection[Interval<real>, Interval<real>] => Interval<real>`
- `intervalIntersection[Interval<integer>, Interval<real>] => Interval<real>`
- `intervalIntersection[Interval<real>, Interval<integer>] => Interval<real>`
- `intervalIntersection[Interval<integer>, Interval<integer>] => Interval<integer>`

### intervalIsBounded

Namespace: Interval. Declared base cost: 1 operations.

- `intervalIsBounded[Interval] => boolean`

### intervalIsClosed

Namespace: Interval. Declared base cost: 1 operations.

- `intervalIsClosed[Interval] => boolean`

### intervalIsEmpty

Namespace: Interval. Declared base cost: 1 operations.

- `intervalIsEmpty[Interval] => boolean`

### intervalIsLeftBounded

Namespace: Interval. Declared base cost: 1 operations.

- `intervalIsLeftBounded[Interval] => boolean`

### intervalIsLeftClosed

Namespace: Interval. Declared base cost: 1 operations.

- `intervalIsLeftClosed[Interval] => boolean`

### intervalIsRightBounded

Namespace: Interval. Declared base cost: 1 operations.

- `intervalIsRightBounded[Interval] => boolean`

### intervalIsRightClosed

Namespace: Interval. Declared base cost: 1 operations.

- `intervalIsRightClosed[Interval] => boolean`

### intervalMax

Namespace: Interval. Declared base cost: 1 operations.

- `intervalMax[Interval<real>] => real`
- `intervalMax[Interval<integer>] => integer`

### intervalMin

Namespace: Interval. Declared base cost: 1 operations.

- `intervalMin[Interval<real>] => real`
- `intervalMin[Interval<integer>] => integer`

### intervalSize

Namespace: Interval. Declared base cost: 1 operations.

- `intervalSize[Interval<real>] => real`
- `intervalSize[Interval<integer>] => integer`

### intervalToArray

Namespace: Interval. Declared base cost: 0 operations.

- `intervalToArray[Interval<real>, real] => Array<real>`
- `intervalToArray[Interval<real>] => Array<real>`
- `intervalToArray[Interval<integer>, real] => Array<real>`
- `intervalToArray[Interval<integer>, integer] => Array<integer>`
- `intervalToArray[Interval<integer>] => Array<integer>`

### intervalToSet

Namespace: Interval. Declared base cost: 0 operations.

- `intervalToSet[Interval<real>, real] => Set<real>`
- `intervalToSet[Interval<real>] => Set<real>`
- `intervalToSet[Interval<integer>, real] => Set<real>`
- `intervalToSet[Interval<integer>, integer] => Set<integer>`
- `intervalToSet[Interval<integer>] => Set<integer>`

### isAlive

Namespace: Entity. Declared base cost: 15 operations.

- `isAlive[integer] => boolean`

### isAlly

Namespace: Entity. Declared base cost: 15 operations.

- `isAlly[integer] => boolean`

### isBatchFight

Namespace: Fight. Declared base cost: 10 operations.

- `isBatchFight[] => boolean`

### isChip

Namespace: Chip. Declared base cost: 10 operations.

- `isChip[integer] => boolean`

### isDead

Namespace: Entity. Declared base cost: 15 operations.

- `isDead[integer] => boolean`

### isEmpty

Namespace: Array. Declared base cost: 2 operations.

- `isEmpty[Array] => boolean`

### isEmptyCell

Namespace: Field. Declared base cost: 10 operations.

- `isEmptyCell[integer] => boolean`

### isEnemy

Namespace: Entity. Declared base cost: 15 operations.

- `isEnemy[integer] => boolean`

### isEntity

Namespace: Field. Declared base cost: 10 operations.

- `isEntity[integer] => boolean`

### isFinite

Namespace: Number. Declared base cost: 1 operations.

- `isFinite[real] => boolean`

### isInfinite

Namespace: Number. Declared base cost: 1 operations.

- `isInfinite[real] => boolean`

### isInlineChip

Namespace: Chip. Declared base cost: 10 operations.

- `isInlineChip[integer] => boolean`

### isInlineWeapon

Namespace: Weapon. Declared base cost: 10 operations.

- `isInlineWeapon[integer] => boolean`
- `isInlineWeapon[] => boolean`

### isNaN

Namespace: Number. Declared base cost: 1 operations.

- `isNaN[real] => boolean`

### isObstacle

Namespace: Field. Declared base cost: 10 operations.

- `isObstacle[integer] => boolean`

### isOnSameLine

Namespace: Field. Declared base cost: 15 operations.

- `isOnSameLine[integer, integer] => boolean`

### isPermutation

Namespace: Number. Declared base cost: 10 operations.

- `isPermutation[integer, integer] => boolean`

### isStatic

Namespace: Entity. Declared base cost: 15 operations.

- `isStatic[integer?] => boolean`
- `isStatic[] => boolean`

### isSummon

Namespace: Entity. Declared base cost: 10 operations.

- `isSummon[integer?] => boolean?`
- `isSummon[] => boolean`

### isWeapon

Namespace: Weapon. Declared base cost: 15 operations.

- `isWeapon[integer] => boolean`

### join

Namespace: Array. Declared base cost: 0 operations.

- `join[Array, string] => string`

### jsonDecode

Namespace: JSON. Declared base cost: 0 operations.

- `jsonDecode[string] => any`

### jsonEncode

Namespace: JSON. Declared base cost: 0 operations.

- `jsonEncode[any] => string`

### lama

Namespace: Entity. Declared base cost: 30 operations.

- `lama[] => void`

### leadingZeros

Namespace: Number. Declared base cost: 1 operations.

- `leadingZeros[integer] => integer`

### length

Namespace: String. Declared base cost: 1 operations.

- `length[string] => integer`

### lineOfSight

Namespace: Field. Declared base cost: 31 operations.

- `lineOfSight[integer, integer, null | Array<integer> | integer] => boolean?`
- `lineOfSight[integer, integer] => boolean?`

### listen

Namespace: Entity. Declared base cost: 78 operations.

- `listen[] => Array<Array>`

### log

Namespace: Number. Declared base cost: 4 operations.

- `log[real] => real`

### log10

Namespace: Number. Declared base cost: 5 operations.

- `log10[real] => real`

### log2

Namespace: Number. Declared base cost: 5 operations.

- `log2[real] => real`

### mapAverage

Namespace: Map. Declared base cost: 0 operations.

- `mapAverage[Map] => real`

### mapClear

Namespace: Map. Declared base cost: 1 operations.

- `mapClear[Map] => Map`

### mapContains

Namespace: Map. Declared base cost: 0 operations.

- `mapContains[Map, any] => boolean`

### mapContainsKey

Namespace: Map. Declared base cost: 1 operations.

- `mapContainsKey[Map, any] => boolean`

### mapEvery

Namespace: Map. Declared base cost: 0 operations.

- `mapEvery[Map, Function<any, any, Map => any>] => boolean`

### mapFill

Namespace: Map. Declared base cost: 0 operations.

- `mapFill[Map, any] => void`

### mapFilter

Namespace: Map. Declared base cost: 0 operations.

- `mapFilter[Map, Function<any, any, Map => boolean>] => Map`

### mapFold

Namespace: Map. Declared base cost: 0 operations.

- `mapFold[Map, Function<any, any, any, Map => any>, any] => any`

### mapGet

Namespace: Map. Declared base cost: 2 operations.

- `mapGet[Map, any, any] => any`
- `mapGet[Map, any] => any`

### mapIsEmpty

Namespace: Map. Declared base cost: 2 operations.

- `mapIsEmpty[Map] => boolean`

### mapIter

Namespace: Map. Declared base cost: 0 operations.

- `mapIter[Map, Function<any, any, Map => any>] => void`

### mapKeys

Namespace: Map. Declared base cost: 0 operations.

- `mapKeys[Map] => Array`

### mapMap

Namespace: Map. Declared base cost: 0 operations.

- `mapMap[Map, Function<any, any, Map => any>] => Map`

### mapMax

Namespace: Map. Declared base cost: 0 operations.

- `mapMax[Map] => any`

### mapMerge

Namespace: Map. Declared base cost: 0 operations.

- `mapMerge[Map, Map] => any`

### mapMin

Namespace: Map. Declared base cost: 0 operations.

- `mapMin[Map] => any`

### mapPut

Namespace: Map. Declared base cost: 3 operations.

- `mapPut[Map, any, any] => any`

### mapPutAll

Namespace: Map. Declared base cost: 0 operations.

- `mapPutAll[Map, Map] => void`

### mapRemove

Namespace: Map. Declared base cost: 2 operations.

- `mapRemove[Map, any] => any`

### mapRemoveAll

Namespace: Map. Declared base cost: 0 operations.

- `mapRemoveAll[Map, any] => void`

### mapReplace

Namespace: Map. Declared base cost: 3 operations.

- `mapReplace[Map, any, any] => any`

### mapReplaceAll

Namespace: Map. Declared base cost: 0 operations.

- `mapReplaceAll[Map, Map] => void`

### mapSearch

Namespace: Map. Declared base cost: 0 operations.

- `mapSearch[Map, any] => any`

### mapSize

Namespace: Map. Declared base cost: 1 operations.

- `mapSize[Map] => integer`

### mapSome

Namespace: Map. Declared base cost: 0 operations.

- `mapSome[Map, Function<any, any, Map => any>] => boolean`

### mapSum

Namespace: Map. Declared base cost: 0 operations.

- `mapSum[Map] => real`

### mapValues

Namespace: Map. Declared base cost: 0 operations.

- `mapValues[Map] => Array`

### mark

Namespace: Util. Declared base cost: 164 operations.

- `mark[Array<integer> | integer, integer, integer] => boolean`
- `mark[Array<integer> | integer, integer] => boolean`
- `mark[Array<integer> | integer] => boolean`

### markText

Namespace: Util. Declared base cost: 164 operations.

- `markText[Array<integer> | integer, any, integer, integer] => boolean`
- `markText[Array<integer> | integer, any, integer] => boolean`
- `markText[Array<integer> | integer, any] => boolean`
- `markText[Array<integer> | integer] => boolean`

### max

Namespace: Number. Declared base cost: 1 operations.

- `max[real, real] => real`
- `max[integer, integer] => integer`
- `max[big_integer, big_integer] => big_integer`

### min

Namespace: Number. Declared base cost: 1 operations.

- `min[real, real] => real`
- `min[integer, integer] => integer`
- `min[big_integer, big_integer] => big_integer`

### moveAwayFrom

Namespace: Fight. Declared base cost: 500 operations.

- `moveAwayFrom[integer, integer] => integer`
- `moveAwayFrom[integer] => integer`

### moveAwayFromCell

Namespace: Fight. Declared base cost: 500 operations.

- `moveAwayFromCell[integer, integer] => integer`
- `moveAwayFromCell[integer] => integer`

### moveAwayFromCells

Namespace: Fight. Declared base cost: 500 operations.

- `moveAwayFromCells[Array<integer>, integer] => integer`
- `moveAwayFromCells[Array<integer>] => integer`

### moveAwayFromEntities

Namespace: Fight. Declared base cost: 500 operations.

- `moveAwayFromEntities[Array<integer>, integer] => integer`
- `moveAwayFromEntities[Array<integer>] => integer`

### moveAwayFromLeeks

Namespace: Fight. Declared base cost: 500 operations.

- `moveAwayFromLeeks[Array<integer>, integer] => integer`
- `moveAwayFromLeeks[Array<integer>] => integer`

### moveAwayFromLine

Namespace: Fight. Declared base cost: 500 operations.

- `moveAwayFromLine[integer, integer, integer] => integer`
- `moveAwayFromLine[integer, integer] => integer`

### moveToward

Namespace: Fight. Declared base cost: 500 operations.

- `moveToward[integer, integer] => integer`
- `moveToward[integer] => integer`

### moveTowardCell

Namespace: Fight. Declared base cost: 500 operations.

- `moveTowardCell[integer, integer] => integer`
- `moveTowardCell[integer] => integer`

### moveTowardCells

Namespace: Fight. Declared base cost: 500 operations.

- `moveTowardCells[Array<integer>, integer] => integer`
- `moveTowardCells[Array<integer>] => integer`

### moveTowardEntities

Namespace: Fight. Declared base cost: 500 operations.

- `moveTowardEntities[Array<integer>, integer] => integer`
- `moveTowardEntities[Array<integer>] => integer`

### moveTowardLeeks

Namespace: Fight. Declared base cost: 500 operations.

- `moveTowardLeeks[Array<integer>, integer] => integer`
- `moveTowardLeeks[Array<integer>] => integer`

### moveTowardLine

Namespace: Fight. Declared base cost: 500 operations.

- `moveTowardLine[integer, integer, integer] => integer`
- `moveTowardLine[integer, integer] => integer`

### number

Namespace: Value. Declared base cost: 3 operations.

- `number[any] => real | integer`

### pause

Namespace: Util. Declared base cost: 30 operations.

- `pause[] => void`

### pop

Namespace: Array. Declared base cost: 2 operations.

- `pop[Array] => any`

### pow

Namespace: Number. Declared base cost: 7 operations.

- `pow[real, real] => real`
- `pow[big_integer, big_integer] => big_integer`

### push

Namespace: Array. Declared base cost: 2 operations.

- `push[Array, any] => void`

### pushAll

Namespace: Array. Declared base cost: 0 operations.

- `pushAll[Array, Array] => void`

### rand

Namespace: Number. Declared base cost: 3 operations.

- `rand[] => real`

### randInt

Namespace: Number. Declared base cost: 2 operations.

- `randInt[integer, integer] => integer`

### randReal

Namespace: Number. Declared base cost: 3 operations.

- `randReal[real, real] => real`

### realBits

Namespace: Number. Declared base cost: 1 operations.

- `realBits[real] => integer`

### remove

Namespace: Array. Declared base cost: 0 operations.

- `remove[Array, integer] => any`

### removeElement

Namespace: Array. Declared base cost: 0 operations.

- `removeElement[Array, any] => void`

### replace

Namespace: String. Declared base cost: 0 operations.

- `replace[string, string, string] => string`

### resurrect

Namespace: Chip. Declared base cost: 500 operations.

- `resurrect[integer, integer] => integer`

### reverse

Namespace: Array. Declared base cost: 0 operations.

- `reverse[Array] => void`

### rotateLeft

Namespace: Number. Declared base cost: 1 operations.

- `rotateLeft[integer, integer] => integer`

### rotateRight

Namespace: Number. Declared base cost: 1 operations.

- `rotateRight[integer, integer] => integer`

### round

Namespace: Number. Declared base cost: 1 operations.

- `round[real] => integer`
- `round[integer] => integer`

### say

Namespace: Entity. Declared base cost: 30 operations.

- `say[any] => boolean`

### search

Namespace: Array. Declared base cost: 0 operations.

- `search[Array, any, integer] => any`
- `search[Array, any] => any`

### sendAll

Namespace: Network. Declared base cost: 40 operations.

- `sendAll[integer, any] => void`

### sendTo

Namespace: Network. Declared base cost: 15 operations.

- `sendTo[integer, integer, any] => boolean`

### setBit

Namespace: Number. Declared base cost: 1 operations.

- `setBit[integer, integer] => integer`
- `setBit[integer, integer, integer] => integer`
- `setBit[integer, integer, boolean] => integer`
- `setBit[big_integer, integer] => big_integer`
- `setBit[big_integer, integer, integer] => big_integer`
- `setBit[big_integer, integer, boolean] => big_integer`

### setClear

Namespace: Set. Declared base cost: 1 operations.

- `setClear[Set] => Set`

### setContains

Namespace: Set. Declared base cost: 1 operations.

- `setContains[Set, any] => boolean`

### setDifference

Namespace: Set. Declared base cost: 0 operations.

- `setDifference[Set, Set] => Set`

### setDisjunction

Namespace: Set. Declared base cost: 0 operations.

- `setDisjunction[Set, Set] => Set`

### setFilter

Namespace: Set. Declared base cost: 0 operations.

- `setFilter[Set, Function<any, Set => boolean>] => Set`

### setIntersection

Namespace: Set. Declared base cost: 0 operations.

- `setIntersection[Set, Set] => Set`

### setIsEmpty

Namespace: Set. Declared base cost: 1 operations.

- `setIsEmpty[Set] => boolean`

### setIsSubsetOf

Namespace: Set. Declared base cost: 0 operations.

- `setIsSubsetOf[Set, Set] => boolean`

### setLoadout

Namespace: Fight. Declared base cost: 100 operations.

- `setLoadout[string] => boolean`
- `setLoadout[string, boolean] => boolean`

### setPut

Namespace: Set. Declared base cost: 3 operations.

- `setPut[Set, any] => boolean`

### setRegister

Namespace: Util. Declared base cost: 50 operations.

- `setRegister[string, any] => boolean`

### setRemove

Namespace: Set. Declared base cost: 2 operations.

- `setRemove[Set, any] => boolean`

### setSize

Namespace: Set. Declared base cost: 1 operations.

- `setSize[Set] => integer`

### setToArray

Namespace: Set. Declared base cost: 0 operations.

- `setToArray[Set] => Array`

### setUnion

Namespace: Set. Declared base cost: 0 operations.

- `setUnion[Set, Set] => Set`

### setWeapon

Namespace: Entity. Declared base cost: 15 operations.

- `setWeapon[integer] => boolean`

### shift

Namespace: Array. Declared base cost: 0 operations.

- `shift[Array] => any`

### show

Namespace: Util. Declared base cost: 0 operations.

- `show[integer, integer] => boolean`
- `show[integer] => boolean`

### shuffle

Namespace: Array. Declared base cost: 0 operations.

- `shuffle[Array] => void`

### signum

Namespace: Number. Declared base cost: 1 operations.

- `signum[real] => integer`
- `signum[integer] => integer`
- `signum[big_integer] => integer`

### sin

Namespace: Number. Declared base cost: 3 operations.

- `sin[real] => real`

### sort

Namespace: Array. Declared base cost: 0 operations.

- `sort[Array, integer] => void`
- `sort[Array] => void`

### split

Namespace: String. Declared base cost: 0 operations.

- `split[string, string, integer] => Array<string>`
- `split[string, string] => Array<string>`

### sqrt

Namespace: Number. Declared base cost: 3 operations.

- `sqrt[real] => real`

### startsWith

Namespace: String. Declared base cost: 0 operations.

- `startsWith[string, string] => boolean`

### string

Namespace: Value. Declared base cost: 6 operations.

- `string[any] => string`

### substring

Namespace: String. Declared base cost: 0 operations.

- `substring[string, integer, integer] => string`
- `substring[string, integer] => string`

### sum

Namespace: Array. Declared base cost: 0 operations.

- `sum[Array] => real`

### summon

Namespace: Chip. Declared base cost: 1750 operations.

- `summon[integer, integer, Function< => any>, string] => integer`
- `summon[integer, integer, Function< => any>] => integer`

### tan

Namespace: Number. Declared base cost: 4 operations.

- `tan[real] => real`

### testBit

Namespace: Number. Declared base cost: 1 operations.

- `testBit[integer, integer] => boolean`
- `testBit[big_integer, integer] => boolean`

### toDegrees

Namespace: Number. Declared base cost: 3 operations.

- `toDegrees[real] => real`

### toFixed

Namespace: Number. Declared base cost: 40 operations.

- `toFixed[real, integer] => string`
- `toFixed[integer, integer] => string`
- `toFixed[big_integer, integer] => string`

### toLower

Namespace: String. Declared base cost: 0 operations.

- `toLower[string] => string`

### toRadians

Namespace: Number. Declared base cost: 3 operations.

- `toRadians[real] => real`

### toUpper

Namespace: String. Declared base cost: 0 operations.

- `toUpper[string] => string`

### trailingZeros

Namespace: Number. Declared base cost: 1 operations.

- `trailingZeros[integer] => integer`
- `trailingZeros[big_integer] => integer`

### trim

Namespace: String. Declared base cost: 5 operations.

- `trim[string] => string`

### typeOf

Namespace: Value. Declared base cost: 1 operations.

- `typeOf[any] => integer`

### unknown

Namespace: Value. Declared base cost: 100 operations.

- `unknown[any] => any`

### unshift

Namespace: Array. Declared base cost: 0 operations.

- `unshift[Array, any] => void`

### useChip

Namespace: Chip. Declared base cost: 3000 operations.

- `useChip[integer, integer] => integer`
- `useChip[integer] => integer`

### useChipOnCell

Namespace: Chip. Declared base cost: 3000 operations.

- `useChipOnCell[integer, integer] => integer`

### useWeapon

Namespace: Weapon. Declared base cost: 3000 operations.

- `useWeapon[integer] => integer`

### useWeaponOnCell

Namespace: Weapon. Declared base cost: 3000 operations.

- `useWeaponOnCell[integer] => integer`

### weaponNeedLos

Namespace: Weapon. Declared base cost: 10 operations.

- `weaponNeedLos[integer] => boolean`
- `weaponNeedLos[] => boolean`

## Constants

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
