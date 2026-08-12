use std::process;
use testgap_worker::{RuntimeConformanceConfig, RuntimeConformanceHarness};

fn main() {
    let config = match RuntimeConformanceConfig::from_environment() {
        Ok(config) => config,
        Err(error) => {
            eprintln!("CONFORMANCE_SETUP=FAIL");
            eprintln!("CONFORMANCE_SETUP_ERROR={error}");
            process::exit(1);
        }
    };
    let report = RuntimeConformanceHarness::new(config).run();
    print!("{}", report.render());
    if report.has_failures() {
        process::exit(1);
    }
}
