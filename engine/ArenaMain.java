package arena.bridge;

import java.nio.file.Files;
import java.nio.file.Path;
import java.io.FileNotFoundException;
import java.util.Map;
import java.util.TreeMap;

import com.leekwars.generator.Generator;
import com.leekwars.generator.FightFunctions;
import com.leekwars.generator.FightConstants;
import com.leekwars.generator.Log;
import com.leekwars.generator.leek.RegisterManager;
import com.leekwars.generator.scenario.Scenario;
import com.leekwars.generator.state.Entity;
import com.leekwars.generator.state.State;
import com.leekwars.generator.test.LocalTrophyManager;
import com.leekwars.generator.util.Json;
import leekscript.compiler.AIFile;
import leekscript.compiler.Folder;
import leekscript.compiler.LeekScript;
import leekscript.compiler.resolver.NativeFileSystem;
import leekscript.runner.LeekFunctions;
import leekscript.runner.LeekConstants;
import tools.jackson.databind.node.ObjectNode;

/** Small adapter; upstream sources and game rules stay pinned and untouched. */
public final class ArenaMain {
    /** Each AI can include only files from its own submission. */
    static final class SubmissionFileSystem extends NativeFileSystem {
        private final Map<Integer, Folder> roots = new TreeMap<>();
        Folder root(int owner) {
            return roots.computeIfAbsent(owner, id -> {
                var f = new Folder(id, id, "strategies/" + id, null, null, this, 0);
                f.setParent(f);
                f.setRoot(f);
                return f;
            });
        }
        @Override public Folder getRoot() { return root(1); }
        @Override public Folder getRoot(int owner) { return root(owner); }
        @Override public Folder getRoot(int owner, int farmer) { return root(owner); }
        @Override public Folder getFolderById(int id, int farmer) { return root(farmer); }
        private boolean allowed(String name, Folder folder) {
            try {
                var path = Path.of(folder.getName()).resolve(name).toRealPath();
                return path.startsWith(Path.of(root(folder.getOwner()).getName()).toRealPath());
            } catch (Exception e) { return false; }
        }
        @Override public Folder findFolder(String name, Folder folder) {
            if (!allowed(name, folder)) return null;
            return new Folder(0, folder.getOwner(), Path.of(folder.getName()).resolve(name).toString(),
                folder, root(folder.getOwner()), this, 0);
        }
        @Override public AIFile findFile(String name, Folder folder) throws FileNotFoundException {
            if (!name.endsWith(".leek") || !allowed(name, folder)) throw new FileNotFoundException(name);
            return super.findFile(name, folder);
        }
    }

    static final class Metrics extends LocalTrophyManager {
        final ObjectNode teams = Json.createObject();
        Metrics() {
            for (int i = 0; i < 2; i++) {
                var t = Json.createObject();
                for (String key : new String[]{"operations", "turn_elapsed_ns", "turns", "errors", "operation_limit_hits", "stack_overflows"}) t.put(key, 0L);
                teams.set(String.valueOf(i), t);
            }
        }
        void add(Entity e, String key, long value) {
            var t = (ObjectNode) teams.get(String.valueOf(e.getTeam()));
            t.put(key, t.get(key).longValue() + value);
        }
        @Override public void addTimes(Entity e, long time, long ops) {
            super.addTimes(e, time, ops);
            add(e, "operations", ops);
            add(e, "turn_elapsed_ns", time);
            add(e, "turns", 1);
        }
        @Override public void error(Entity e) { add(e, "errors", 1); }
        @Override public void tooMuchOperations(Entity e) { add(e, "operation_limit_hits", 1); }
        @Override public void stackOverflow(Entity e) { add(e, "stack_overflows", 1); }
    }

    public static void main(String[] args) throws Exception {
        var result = Json.createObject();
        try {
            Log.enable(false);
            LeekScript.setFileSystem(new SubmissionFileSystem());
            var generator = new Generator();
            generator.setCache(false);
            if (args[0].equals("api")) {
                var functions = Json.createObject();
                var all = new TreeMap<String, LeekFunctions>(LeekFunctions.getStandardFunctions());
                all.putAll(FightFunctions.getFunctions());
                for (var entry : all.entrySet()) {
                    var f = entry.getValue();
                    if (f.getMinVersion() > 4 || f.getMaxVersion() < 4) continue;
                    var item = Json.createObject();
                    item.put("base_operations", f.getOperations());
                    item.put("namespace", f.getStandardClass());
                    var versions = Json.createArray();
                    for (var v : f.getVersions()) versions.add(v.toString());
                    item.set("signatures", versions);
                    functions.set(entry.getKey(), item);
                }
                var constants = Json.createObject();
                for (var c : FightConstants.values()) constants.put(c.name(), c.getValue());
                for (var c : LeekConstants.values()) {
                    // JSON does not represent Infinity/NaN; strings preserve their meaning.
                    constants.put(c.name(), String.valueOf(c.getValue()));
                }
                result.set("functions", functions);
                result.set("constants", constants);
                result.put("success", true);
            } else if (args[0].equals("analyze")) {
                var file = LeekScript.getFileSystem().getRoot(1).resolve(args[1]);
                var analysis = generator.analyzeAI(file, 1);
                result.put("success", analysis.success);
                result.set("diagnostics", analysis.informations);
            } else if (args[0].equals("fight")) {
                var input = Path.of(args[1]);
                var config = Json.parseObject(Files.readString(input));
                var scenario = Scenario.fromFile(input.toFile());
                // Upstream's CLI parser does not currently read these fields.
                scenario.map = config.hasNonNull("map") ? (ObjectNode) config.get("map") : null;
                scenario.type = State.TYPE_TEAM;
                scenario.context = State.CONTEXT_TEST;
                scenario.drawCheckLife = false;
                for (int team = 0; team < scenario.entities.size(); team++) {
                    for (var entity : scenario.entities.get(team)) {
                        entity.aiOwner = team + 1;
                        entity.ai_path = entity.ai;
                        entity.ai_version = 4;
                        entity.ai_strict = false;
                    }
                }
                var metrics = new Metrics();
                // Registers are empty at the start of every match; no database access.
                var registers = new RegisterManager() {
                    public String getRegisters(int id) { return null; }
                    public void saveRegisters(int id, String value, boolean isNew) {}
                };
                var outcome = generator.runScenario(scenario, null, registers, metrics);
                if (outcome.exception != null) throw outcome.exception;
                if (outcome.fight == null) throw new IllegalStateException("No fight outcome");
                result = outcome.toJson();
                result.set("team_metrics", metrics.teams);
                result.put("success", true);
            } else throw new IllegalArgumentException("Unknown command");
        } catch (Exception e) {
            result.put("success", false);
            result.put("infrastructure_error", e.toString());
            e.printStackTrace(System.err);
        }
        Files.writeString(Path.of(args[2]), result.toString());
        if (result.has("infrastructure_error")) System.exit(2);
    }
}
