//! Standard-library process supervision primitives for the TestGap worker.
//!
//! This crate captures raw execution facts. Untrusted execution goes through
//! [`ProcessSupervisor::restricted`], which enforces trusted command,
//! executable, workspace-path, and environment authority before spawn.
//! Trusted local harnesses may explicitly opt into unrestricted behavior via
//! [`ProcessSupervisor::trusted_local`]. This crate is still not a secure
//! sandbox and does not own queue, workflow, evidence, or persistence
//! semantics.

mod adapters;
mod conformance;
mod execution_authority;
mod execution_export;
mod model;
mod producer_result;
mod producer_result_adapter;
mod resource_limits;
mod supervisor;

pub use adapters::*;
pub use conformance::*;
pub use execution_authority::*;
pub use execution_export::*;
pub use model::*;
pub use producer_result::*;
pub use producer_result_adapter::*;
pub use supervisor::{ProcessSupervisor, TrustedLocalExecution};
