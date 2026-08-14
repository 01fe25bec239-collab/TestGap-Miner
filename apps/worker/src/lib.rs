//! Standard-library process supervision primitives for the TestGap worker.
//!
//! This crate captures raw execution facts. It is not a secure sandbox and
//! does not own queue, workflow, evidence, or persistence semantics.

mod adapters;
mod conformance;
mod model;
mod producer_result;
mod supervisor;

pub use adapters::*;
pub use conformance::*;
pub use model::*;
pub use producer_result::*;
pub use supervisor::ProcessSupervisor;
