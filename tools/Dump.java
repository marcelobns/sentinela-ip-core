import com.cburch.logisim.proj.*;
import com.cburch.logisim.circuit.*;
import com.cburch.logisim.comp.*;
import com.cburch.logisim.data.*;
import com.cburch.logisim.instance.StdAttr;
import java.io.File;
public class Dump {
  public static void main(String[] a) throws Exception {
    Project p = ProjectActions.doOpenNoWindow(null, new File(a[0]));
    for (int k = 1; k < a.length; k++) {
      Circuit c = p.getLogisimFile().getCircuit(a[k]);
      System.out.println("CIRCUIT " + a[k]);
      for (Component comp : c.getNonWires()) {
        Bounds b = comp.getBounds();
        Object lab = comp.getAttributeSet().containsAttribute(StdAttr.LABEL) ? comp.getAttributeSet().getValue(StdAttr.LABEL) : "";
        System.out.println("COMP " + comp.getFactory().getName().replace(' ', '_') + " " + b.getX() + " " + b.getY() + " " + b.getWidth() + " " + b.getHeight() + " " + comp.getLocation().getX() + " " + comp.getLocation().getY() + " " + (lab == null || lab.toString().isEmpty() ? "-" : lab));
        for (EndData e : comp.getEnds()) System.out.println("END " + e.getLocation().getX() + " " + e.getLocation().getY() + " " + e.getWidth().getWidth());
      }
      for (Wire w : c.getWires()) System.out.println("WIRE " + w.getEnd0().getX() + " " + w.getEnd0().getY() + " " + w.getEnd1().getX() + " " + w.getEnd1().getY());
    }
    System.exit(0);
  }
}
