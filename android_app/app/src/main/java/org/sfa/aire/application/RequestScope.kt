package org.sfa.aire.application
/** Frontera de resultados de UI. No cancela ni revierte una acción ya aceptada por servidor. */
class RequestScope {
    private var epoch=0L
    @Synchronized fun capture():Long=epoch
    @Synchronized fun invalidate(){epoch++}
    @Synchronized fun accepts(ticket:Long):Boolean=ticket==epoch
}
