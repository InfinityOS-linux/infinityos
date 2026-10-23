import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// these are hacks to make Dash2Dock Animated compatible with other Extensions
//
export const Integrations = class {
  enable() {
    this.hookCompiz();
    this.hookBms();
  }

  disable() {
    this.releaseCompiz();
    this.releaseBms();
  }

  hookCompiz(hook = true) {
    let compiz = Main.extensionManager.lookup(
      'compiz-alike-magic-lamp-effect@hermes83.github.com'
    );
    if (compiz && compiz.stateObj) {
      let stateObj = compiz.stateObj;
      this._compiz = stateObj;
      if (stateObj._getIcon && !hook) {
        stateObj.getIcon = stateObj._getIcon;
        stateObj._getIcon = null;
      }
      if (!stateObj._getIcon && hook) {
        stateObj._getIcon = stateObj.getIcon;
        if (this.extension.lamp_app_animation) {
          stateObj.getIcon = this.compiz_getIcon.bind(this);
        }
      }
    }
  }

  releaseCompiz() {
    this.hookCompiz(false);
    this._compiz = null;
  }

  // override compiz getIcon
  compiz_getIcon(actor) {
    let [success, icon] = actor.meta_window.get_icon_geometry();
    if (success) {
      return icon;
    }

    let docks = this.extension.docks;

    let monitor = Main.layoutManager.monitors[actor.meta_window.get_monitor()];
    let dock = docks.find((d) => d._monitorIndex == monitor.index);

    if (!dock) {
      return { x: monitor.x, y: monitor.y, width: 0, height: 0 };
    }

    let dashIcon = null;

    let sz = dock._preferredIconSize();
    let ofs = 0;
    if (sz) {
      let scale = dock.getMonitor().geometry_scale || 1;
      ofs = (sz / 2) * scale;
    }

    let pids = null;
    let pid = actor.get_meta_window()
      ? actor.get_meta_window().get_pid()
      : null;
    if (pid) {
      dock.dash._box
        .get_children()
        .filter(
          (dashElement) =>
            dashElement.child &&
            dashElement.child._delegate &&
            dashElement.child._delegate.app
        )
        .forEach((dashElement) => {
          pids = dashElement.child._delegate.app.get_pids();
          if (pids && pids.indexOf(pid) >= 0) {
            let renderer = dashElement;
            if (dashElement._renderer) {
              dashElement = dashElement._renderer;
            }
            let transformed_position = dashElement.get_transformed_position();
            if (
              transformed_position &&
              transformed_position[0] &&
              transformed_position[1]
            ) {
              dashIcon = {
                x: transformed_position[0],
                y: transformed_position[1],
                width: 0,
                height: 0,
              };
              return;
            }
          }
        });
    }

    if (!dashIcon) {
      return { x: monitor.x, y: monitor.y, width: 0, height: 0 };
    }

    // console.log('compiz-alike-magic-lamp-effect: getIcon');
    // console.log(`x:${dashIcon.x} y:${dashIcon.y} w:${dashIcon.width} h:${dashIcon.height}`);
    let x = dashIcon.x;
    let y = dashIcon.y;
    let w = 0; //dashIcon.width;
    let h = 0; //dashIcon.height;

    switch (dock._position) {
      case 'left':
        x = dock._monitor.x;
        y += ofs;
        break;
      case 'right':
        x = dock._monitor.x + dock._monitor.width;
        y += ofs;
        break;
      case 'top':
        y = dock._monitor.y;
        x += ofs;
        break;
      case 'bottom':
        y = dock._monitor.y + dock._monitor.height;
        x += ofs;
        break;
    }

    dashIcon = {
      x: x,
      y: y,
      width: w,
      height: h,
    };

    return dashIcon;
  }

  hookBms(hook = true) {
    if (!hook) {
      this.extension.docks.forEach((dock) => {
        dock.animator._bms = null;
      });
    }

    let bms = Main.extensionManager.lookup('blur-my-shell@aunetx');
    this._bms = bms;
    if (bms && bms.stateObj && bms.metadata.version >= 70) {
      let obj = bms.stateObj;
      if (obj._dash_to_dock_blur) {
        if (!obj._dash_to_dock_blur.update_size_orig) {
          obj._dash_to_dock_blur.update_size_orig =
            obj._dash_to_dock_blur.update_size;
        }
        if (hook && this.extension.blur_background) {
          obj._dash_to_dock_blur.update_size = () => {};
        } else if (obj._dash_to_dock_blur.update_size_orig) {
          obj._dash_to_dock_blur.update_size =
            obj._dash_to_dock_blur.update_size_orig;
        }
      }
    }
  }

  releaseBms() {
    this.hookBms(false);
    this._bms = null;
  }

  bms_update_size(animator) {
    // Blur My Shell's rectangular surface can show outside the dock's rounded
    // background in both color schemes. The dock paints its own pill instead.
    const bms = animator.dock.get_children().find(child =>
      child.get_name() === 'bms-dash-backgroundgroup');
    animator._bms = bms;
    if (bms) bms.visible = false;
  }
};
