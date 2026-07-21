// POSITIVE CONTROL fixture (transitive-lockfile case). The SOURCE is clean and
// the manifest declares nothing denied — the OSC crate arrives only through the
// resolved dependency graph, which is precisely how a rogue networking crate
// would enter without anyone editing Cargo.toml.

fn main() {
    println!("shell start");
}
