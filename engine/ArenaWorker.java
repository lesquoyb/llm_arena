package arena.bridge;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * One JVM serving matches one at a time, with a fresh source workspace per match.
 *
 * By default each match gets a fresh game/compiler classloader. With
 * -Darena.sharedEngine=true the engine classes stay loaded (and JIT-compiled)
 * across matches, and with -Darena.aiCache=true upstream's compiled-AI cache
 * (the ai/ directory and its in-memory twin) reuses a strategy's bytecode while
 * its sources are unchanged. Replays were checked identical to the per-match
 * mode on stored competition fights. A match that fails discards the shared
 * classloader, so later matches never inherit its state.
 */
public final class ArenaWorker {
    static final boolean SHARED = Boolean.getBoolean("arena.sharedEngine");
    /** Runtime-compiled AI loaders use the system loader as their parent. */
    public static final class DispatchLoader extends ClassLoader {
        static volatile ClassLoader target;
        public DispatchLoader(ClassLoader parent) { super(parent); }
        @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
            var current = target;
            if (current != null && !name.startsWith("arena.bridge.ArenaWorker")) {
                try { return current.loadClass(name); } catch (ClassNotFoundException missing) { /* platform fallback */ }
            }
            return super.loadClass(name, resolve);
        }
    }
    static void remove(Path path) throws IOException {
        if (!Files.exists(path)) return;
        try (var paths = Files.walk(path)) {
            for (var item : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(item);
        }
    }
    static void copy(Path source, Path target) throws IOException {
        try (var paths = Files.walk(source)) {
            for (var item : paths.toList()) {
                var destination = target.resolve(source.relativize(item));
                if (Files.isDirectory(item)) Files.createDirectories(destination);
                else Files.copy(item, destination, StandardCopyOption.REPLACE_EXISTING);
            }
        }
    }
    public static void main(String[] args) throws Exception {
        var control = System.out; var originalError = System.err;
        var input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        var urls = Arrays.stream(System.getProperty("java.class.path").split(File.pathSeparator))
            .map(value -> { try { return Path.of(value).toUri().toURL(); } catch (Exception e) { throw new RuntimeException(e); } })
            .toArray(URL[]::new);
        control.println("READY"); control.flush();
        // Kept between requests: pinned data, and with the AI cache its compiled classes.
        var kept = Set.of("data", "worker-startup.log", "ai");
        URLClassLoader shared = null;
        String line;
        while ((line = input.readLine()) != null) {
            var values = Arrays.stream(line.split("\\t", -1))
                .map(value -> new String(Base64.getDecoder().decode(value), StandardCharsets.UTF_8)).toArray(String[]::new);
            var work = Path.of(values[2]);
            // Keep only pinned data between requests, including after compiler errors.
            try (var paths = Files.list(Path.of("."))) {
                for (var path : paths.toList()) if (!kept.contains(path.getFileName().toString())) remove(path);
            }
            copy(work.resolve("strategies"), Path.of("strategies"));
            if (values[0].equals("fight")) Files.copy(work.resolve(values[1]), Path.of(values[1]));
            var loader = SHARED && shared != null ? shared : new URLClassLoader(urls, ClassLoader.getPlatformClassLoader());
            boolean succeeded = false;
            try (var stdout = new PrintStream(Files.newOutputStream(work.resolve("stdout.log")), true, StandardCharsets.UTF_8);
                 var stderr = new PrintStream(Files.newOutputStream(work.resolve("stderr.log")), true, StandardCharsets.UTF_8)) {
                System.setOut(stdout); System.setErr(stderr);
                var thread = Thread.currentThread(); var previous = thread.getContextClassLoader();
                try {
                    thread.setContextClassLoader(loader); DispatchLoader.target=loader;
                    loader.loadClass("arena.bridge.ArenaMain").getMethod("main", String[].class)
                        .invoke(null, (Object) new String[]{values[0], values[1], "outcome.json"});
                    succeeded = true;
                } finally {
                    DispatchLoader.target=null; thread.setContextClassLoader(previous); System.setOut(control); System.setErr(originalError);
                }
            } finally {
                if (SHARED && succeeded) shared = loader;
                else { loader.close(); if (loader == shared) shared = null; }
            }
            Files.copy(Path.of("outcome.json"), work.resolve("outcome.json"), StandardCopyOption.REPLACE_EXISTING);
            control.println("DONE"); control.flush();
        }
    }
}
