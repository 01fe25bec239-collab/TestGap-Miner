//! Standard-library process supervision primitives for the TestGap worker.
//!
//! This crate captures raw execution facts. It is not a secure sandbox and
//! does not own queue, workflow, evidence, or persistence semantics.

mod adapters;
mod model;
mod supervisor;

pub use adapters::*;
pub use model::*;
pub use supervisor::ProcessSupervisor;
