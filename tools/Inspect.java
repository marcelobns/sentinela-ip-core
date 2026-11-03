import com.cburch.logisim.proj.*;
import com.cburch.logisim.circuit.*;
import com.cburch.logisim.comp.*;
import com.cburch.logisim.instance.*;
import java.io.File;
public class Inspect {
  public static void main(String[] a) throws Exception {
    Project p = ProjectActions.doOpenNoWindow(null, new File(a[0]));
    Circuit c = p.getLogisimFile().getCircuit(a[1]);
    for (Component comp : c.getNonWires()) {
      System.out.println(comp.getFactory().getName() + " @" + comp.getLocation() + " bounds=" + comp.getBounds());
      java.util.List<Port> ports = null; if (comp instanceof InstanceComponent ic) { try { var m = InstanceComponent.class.getDeclaredMethod("getPorts"); m.setAccessible(true); ports = (java.util.List<Port>) m.invoke(ic);} catch (Exception ex) {} }
      int i = 0;
      for (EndData e : comp.getEnds()) {
        String tip = "";
        if (ports != null && i < ports.size() && ports.get(i).getToolTip() != null) tip = ports.get(i).getToolTip().toString();
        System.out.println("   end" + i + " " + e.getLocation() + " w=" + e.getWidth().getWidth() + (e.isInput()?" in":"") + (e.isOutput()?" out":"") + "  " + tip);
        i++;
      }
    }
    System.exit(0);
  }
}
