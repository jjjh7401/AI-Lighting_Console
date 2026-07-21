// POSITIVE CONTROL fixture — this file MUST be flagged by the deny-all scan.
// It is the Rust twin of the Python synthetic-bypass module in
// test_deploy_safety_invariants.py: a shell path that reaches the console
// directly, bypassing the Python safety gate entirely.

use std::net::UdpSocket;

fn push_command() -> std::io::Result<()> {
    let socket = UdpSocket::bind("0.0.0.0:0")?;
    socket.send_to(b"/copilot/cmd\0", "127.0.0.1:8000")?;
    Ok(())
}

fn osc_client() {
    let message = rosc::OscMessage {
        addr: "/copilot/cmd".to_string(),
        args: vec![],
    };
    let _ = rosc::encoder::encode(&rosc::OscPacket::Message(message));
}

fn main() {
    let _ = push_command();
    osc_client();
}
