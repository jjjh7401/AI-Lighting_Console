// POSITIVE CONTROL fixture (credential case). The NETWORK surface is clean on
// purpose: no UdpSocket, no std net import, no raw send, no OSC crate, no
// loopback or console-port literal. The violation is a SECOND, independent
// invariant — key custody is Python-side ONLY (the sidecar reaches the OS
// credential store through Python `keyring`), so a Rust shell that reads the
// store itself has broken AC-DEPLOY-028 ① even though it never opens a socket.
//
// Both layers of the same breach are present: the high-level `keyring` crate
// and a direct Security.framework call one layer lower.

use keyring::Entry;

extern "C" {
    fn SecItemCopyMatching(query: *const u8, result: *mut u8) -> i32;
}

fn read_stored_provider_key() -> Option<String> {
    let entry = Entry::new("com.grandma3copilot.app", "anthropic").ok()?;
    entry.get_password().ok()
}

fn raw_keychain_lookup() -> i32 {
    unsafe { SecItemCopyMatching(std::ptr::null(), std::ptr::null_mut()) }
}

fn main() {
    println!("{:?}", read_stored_provider_key());
    println!("{}", raw_keychain_lookup());
}
